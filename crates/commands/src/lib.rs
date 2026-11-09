//! All document mutations commit through this engine.
use house_core::*;
use house_geometry::{length, validate};
use serde::{Deserialize, Serialize};
#[derive(Clone, Debug, Serialize, Deserialize)]
pub enum Command {
    CreateWall(Wall),
    UpdateWall(Wall),
    MoveWall { id: Id, dx: f64, dy: f64 },
    CreateDoor(Door),
    UpdateDoor(Door),
    CreateWindow(Window),
    UpdateWindow(Window),
    CreateFixture(Fixture),
    UpdateFixture(Fixture),
    CreateRoom(Room),
    CreateRoomLabel(RoomLabel),
    RenameRoom { id: Id, name: String },
    DeleteObject { id: Id },
}
pub struct Engine {
    document: Document,
    undo: Vec<Document>,
    redo: Vec<Document>,
}
impl Engine {
    pub fn new(document: Document) -> Result<Self, String> {
        validate(&document)?;
        Ok(Self {
            document,
            undo: vec![],
            redo: vec![],
        })
    }
    pub fn document(&self) -> &Document {
        &self.document
    }
    /// Opening a project resets history but retains a monotonically increasing live revision.
    pub fn replace(&mut self, mut d: Document) -> Result<(), String> {
        validate(&d)?;
        d.revision = self.next_revision()?;
        self.document = d;
        self.undo.clear();
        self.redo.clear();
        Ok(())
    }
    fn next_revision(&self) -> Result<u64, String> {
        self.document
            .revision
            .checked_add(1)
            .ok_or("Revision overflow".into())
    }
    pub fn execute(&mut self, command: Command) -> Result<u64, String> {
        self.transaction(&[command])
    }
    /// Reject a proposal based on an obsolete document before applying any changes.
    pub fn execute_at_revision(
        &mut self,
        command: Command,
        expected_revision: u64,
    ) -> Result<u64, String> {
        if self.document.revision != expected_revision {
            return Err(format!(
                "Revision conflict: expected {expected_revision}, current {}. Read the document and retry.",
                self.document.revision
            ));
        }
        self.execute(command)
    }
    pub fn transaction(&mut self, commands: &[Command]) -> Result<u64, String> {
        if commands.is_empty() {
            return Err("Empty transaction".into());
        }
        let mut next = self.document.clone();
        for c in commands {
            apply(&mut next, c)?;
        }
        validate(&next)?;
        next.revision = self.next_revision()?;
        self.undo.push(std::mem::replace(&mut self.document, next));
        self.redo.clear();
        Ok(self.document.revision)
    }
    pub fn undo(&mut self) -> Result<u64, String> {
        let rev = self.next_revision()?;
        let mut prev = self.undo.pop().ok_or("Nothing to undo")?;
        prev.revision = rev;
        self.redo.push(std::mem::replace(&mut self.document, prev));
        Ok(rev)
    }
    pub fn redo(&mut self) -> Result<u64, String> {
        let rev = self.next_revision()?;
        let mut next = self.redo.pop().ok_or("Nothing to redo")?;
        next.revision = rev;
        self.undo.push(std::mem::replace(&mut self.document, next));
        Ok(rev)
    }
}
fn apply(d: &mut Document, c: &Command) -> Result<(), String> {
    match c {
        Command::CreateWall(w) => {
            if d.walls.contains_key(&w.id) {
                return Err("Wall already exists".into());
            }
            d.walls.insert(w.id, w.clone());
        }
        Command::UpdateWall(w) => {
            let old = d.walls.get(&w.id).ok_or("Wall not found")?;
            let ratio = length(w) / length(old);
            // Keep openings at the same fractional station when changing a wall's length.
            for door in d.doors.values_mut().filter(|v| v.wall == w.id) {
                door.position *= ratio;
            }
            for window in d.windows.values_mut().filter(|v| v.wall == w.id) {
                window.position *= ratio;
            }
            d.walls.insert(w.id, w.clone());
        }
        Command::MoveWall { id, dx, dy } => {
            let w = d.walls.get_mut(id).ok_or("Wall not found")?;
            w.start.x += dx;
            w.end.x += dx;
            w.start.y += dy;
            w.end.y += dy;
        }
        Command::CreateDoor(v) => {
            if d.doors.contains_key(&v.id) {
                return Err("Door already exists".into());
            }
            d.doors.insert(v.id, v.clone());
        }
        Command::UpdateDoor(v) => {
            if !d.doors.contains_key(&v.id) {
                return Err("Door not found".into());
            }
            d.doors.insert(v.id, v.clone());
        }
        Command::CreateWindow(v) => {
            if d.windows.contains_key(&v.id) {
                return Err("Window already exists".into());
            }
            d.windows.insert(v.id, v.clone());
        }
        Command::UpdateWindow(v) => {
            if !d.windows.contains_key(&v.id) {
                return Err("Window not found".into());
            }
            d.windows.insert(v.id, v.clone());
        }
        Command::CreateFixture(v) => {
            if d.fixtures.contains_key(&v.id) {
                return Err("Fixture already exists".into());
            }
            d.fixtures.insert(v.id, v.clone());
        }
        Command::UpdateFixture(v) => {
            if !d.fixtures.contains_key(&v.id) {
                return Err("Fixture not found".into());
            }
            d.fixtures.insert(v.id, v.clone());
        }
        Command::CreateRoomLabel(label) => {
            if d.room_labels.contains_key(&label.id) {
                return Err("Room label already exists".into());
            }
            d.room_labels.insert(label.id, label.clone());
        }
        Command::CreateRoom(room) => {
            if d.rooms.contains_key(&room.id) {
                return Err("Room already exists".into());
            }
            d.rooms.insert(room.id, room.clone());
        }
        Command::RenameRoom { id, name } => {
            if let Some(room) = d.rooms.get_mut(id) {
                room.name = name.clone();
            } else {
                d.room_labels.get_mut(id).ok_or("Room not found")?.name = name.clone();
            }
        }
        Command::DeleteObject { id } => {
            // Referenced objects cannot be deleted silently; delete dependents in the same transaction first.
            if d.walls.remove(id).is_none()
                && d.doors.remove(id).is_none()
                && d.windows.remove(id).is_none()
                && d.fixtures.remove(id).is_none()
                && d.rooms.remove(id).is_none()
                && d.room_labels.remove(id).is_none()
                && d.dimensions.remove(id).is_none()
                && d.layers.remove(id).is_none()
            {
                return Err("Object not found".into());
            }
        }
    }
    Ok(())
}
#[cfg(test)]
mod tests {
    use super::*;
    use house_geometry::{dimension_value, room_bounds};
    #[test]
    fn bathroom_move_undo() {
        let mut e = Engine::new(bathroom()).unwrap();
        let before = e.document().clone();
        let id = before
            .walls
            .values()
            .find(|w| w.name == "Partition")
            .unwrap()
            .id;
        e.execute(Command::MoveWall {
            id,
            dx: inches(6.0),
            dy: 0.0,
        })
        .unwrap();
        let after = e.document();
        assert_eq!(after.walls[&id].start.x, inches(66.0) + inches(6.0));
        assert_eq!(before.doors, after.doors);
        for r in before.rooms.values() {
            let a = room_bounds(&before, r).unwrap();
            let b = room_bounds(after, r).unwrap();
            let delta = if r.east == id {
                inches(6.0)
            } else {
                -inches(6.0)
            };
            assert!((b.width - a.width - delta).abs() < 1e-9);
            assert!((b.area() - a.area() - delta * inches(96.0)).abs() < 1e-6);
        }
        for dim in before.dimensions.values() {
            assert!(dimension_value(after, dim).unwrap() > 0.0);
        }
        e.undo().unwrap();
        let mut restored = e.document().clone();
        restored.revision = before.revision;
        assert_eq!(restored, before);
        e.redo().unwrap();
        assert_eq!(e.document().revision, 3);
    }
    #[test]
    fn invalid_transaction_rolls_back() {
        let mut e = Engine::new(bathroom()).unwrap();
        let before = e.document().clone();
        let id = before
            .walls
            .values()
            .find(|w| w.name == "Partition")
            .unwrap()
            .id;
        assert!(
            e.transaction(&[
                Command::MoveWall {
                    id,
                    dx: 10.0,
                    dy: 0.0
                },
                Command::MoveWall {
                    id,
                    dx: 10000.0,
                    dy: 0.0
                }
            ])
            .is_err()
        );
        assert_eq!(e.document(), &before);
        assert!(e.undo().is_err());
    }
    #[test]
    fn attachments_follow_and_invalid_resize_rolls_back() {
        let mut e = Engine::new(bathroom()).unwrap();
        let door = e.document().doors.values().next().unwrap().clone();
        let wall = e.document().walls[&door.wall].clone();
        // A detached test wall is free to translate and rotate without room constraints.
        let mut w = wall.clone();
        w.id = Id::new_v4();
        w.start = Point::new(5000.0, 0.0);
        w.end = Point::new(5000.0, 3000.0);
        e.execute(Command::CreateWall(w.clone())).unwrap();
        let mut v = door;
        v.id = Id::new_v4();
        v.wall = w.id;
        v.position = 1500.0;
        e.execute(Command::CreateDoor(v.clone())).unwrap();
        e.execute(Command::MoveWall {
            id: w.id,
            dx: 152.4,
            dy: 40.0,
        })
        .unwrap();
        assert_eq!(e.document().doors[&v.id], v);
        w.start = Point::new(5000.0, 0.0);
        w.end = Point::new(8000.0, 0.0);
        e.execute(Command::UpdateWall(w.clone())).unwrap();
        assert_eq!(e.document().doors[&v.id].position, 1500.0);
        w.end = Point::new(5100.0, 0.0);
        let before = e.document().clone();
        assert!(e.execute(Command::UpdateWall(w)).is_err());
        assert_eq!(e.document(), &before);
    }
}
#[cfg(test)]
mod operation_tests {
    use super::*;
    #[test]
    fn door_updates_delete_and_history() {
        let mut e = Engine::new(bathroom()).unwrap();
        let before = e.document().clone();
        let mut v = before.doors.values().next().unwrap().clone();
        v.position += 25.4;
        v.width -= 10.0;
        v.swing = Swing::Right;
        e.execute(Command::UpdateDoor(v.clone())).unwrap();
        assert_eq!(e.document().doors[&v.id], v);
        let valid = e.document().clone();
        let mut bad = v.clone();
        bad.position = -1.0;
        assert!(e.execute(Command::UpdateDoor(bad)).is_err());
        assert_eq!(e.document(), &valid);
        e.execute(Command::DeleteObject { id: v.id }).unwrap();
        assert!(!e.document().doors.contains_key(&v.id));
        e.undo().unwrap();
        assert_eq!(e.document().doors[&v.id], v);
        e.execute(Command::UpdateDoor(v)).unwrap();
        assert!(e.redo().is_err());
    }
    #[test]
    fn nonfinite_and_invalid_relationships() {
        let mut e = Engine::new(bathroom()).unwrap();
        let original = e.document().clone();
        let w = original.walls.values().next().unwrap().clone();
        assert!(
            e.execute(Command::MoveWall {
                id: w.id,
                dx: f64::NAN,
                dy: 0.0
            })
            .is_err()
        );
        assert!(e.execute(Command::DeleteObject { id: w.id }).is_err());
        let mut bad = w.clone();
        bad.id = Id::new_v4();
        bad.end = bad.start;
        assert!(e.execute(Command::CreateWall(bad)).is_err());
        let door = Door {
            id: Id::new_v4(),
            wall: Id::new_v4(),
            position: 1000.0,
            width: 700.0,
            kind: house_core::DoorKind::Hinged,
            swing: Swing::Left,
        };
        assert!(e.execute(Command::CreateDoor(door)).is_err());
        assert_eq!(e.document(), &original);
    }
    #[test]
    fn length_change_scales_station_and_room_rotation_rejected() {
        let mut d = Document::default();
        let layer = *d.layers.keys().next().unwrap();
        let id = Id::new_v4();
        let wall = Wall {
            id,
            name: "Free".into(),
            start: Point::new(0.0, 0.0),
            end: Point::new(2000.0, 0.0),
            thickness: 100.0,
            layer,
        };
        d.walls.insert(id, wall.clone());
        let v = Door {
            id: Id::new_v4(),
            wall: id,
            position: 1000.0,
            width: 700.0,
            kind: house_core::DoorKind::Hinged,
            swing: Swing::Left,
        };
        d.doors.insert(v.id, v.clone());
        let mut e = Engine::new(d).unwrap();
        let mut changed = wall;
        changed.end.x = 4000.0;
        e.execute(Command::UpdateWall(changed)).unwrap();
        assert_eq!(e.document().doors[&v.id].position, 2000.0);
        e.undo().unwrap();
        assert_eq!(e.document().doors[&v.id].position, 1000.0);
        let mut e = Engine::new(bathroom()).unwrap();
        let before = e.document().clone();
        let mut wall = before
            .walls
            .values()
            .find(|w| w.name == "Partition")
            .unwrap()
            .clone();
        wall.end.x += 25.4;
        assert!(e.execute(Command::UpdateWall(wall)).is_err());
        assert_eq!(e.document(), &before);
    }
    #[test]
    fn multi_object_transaction_validates_final_state() {
        let mut e = Engine::new(bathroom()).unwrap();
        let original = e.document().clone();
        let room = original.rooms.values().next().unwrap();
        let mut commands: Vec<Command> = original
            .dimensions
            .values()
            .filter(|v| v.room == room.id)
            .map(|v| Command::DeleteObject { id: v.id })
            .collect();
        commands.push(Command::DeleteObject { id: room.id });
        e.transaction(&commands).unwrap();
        assert!(!e.document().rooms.contains_key(&room.id));
        e.undo().unwrap();
        let mut restored = e.document().clone();
        restored.revision = original.revision;
        assert_eq!(restored, original);
    }
}

#[cfg(test)]
mod revision_tests {
    use super::*;
    #[test]
    fn stale_edit_preserves_document_and_redo_history() {
        let mut engine = Engine::new(bathroom()).unwrap();
        let id = engine
            .document()
            .walls
            .values()
            .find(|w| w.name == "Partition")
            .unwrap()
            .id;
        let command = Command::MoveWall {
            id,
            dx: 152.4,
            dy: 0.0,
        };
        engine.execute_at_revision(command.clone(), 0).unwrap();
        engine.undo().unwrap();
        let before = engine.document().clone();
        let error = engine.execute_at_revision(command.clone(), 0).unwrap_err();
        assert!(error.contains("Revision conflict: expected 0, current 2"));
        assert_eq!(engine.document(), &before);
        engine.redo().unwrap();
        let moved = engine.document().walls[&id].start.x;
        engine.execute_at_revision(command, 3).unwrap();
        assert_eq!(engine.document().walls[&id].start.x, moved + 152.4);
        assert_eq!(engine.document().revision, 4);
    }
}

#[cfg(test)]
mod fixtures_tests;

#[cfg(test)]
mod room_labels_tests;
