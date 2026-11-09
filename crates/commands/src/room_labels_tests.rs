use super::*;
#[test]
fn room_labels_validate_rename_and_undo_without_changing_walls() {
    let mut engine = Engine::new(bathroom()).unwrap();
    let walls = engine.document().walls.clone();
    let id = Id::new_v4();
    let label = RoomLabel {
        id,
        name: "Living room".into(),
        position: Point::new(100.0, 200.0),
    };
    engine
        .execute(Command::CreateRoomLabel(label.clone()))
        .unwrap();
    engine
        .execute(Command::RenameRoom {
            id,
            name: "Dining room".into(),
        })
        .unwrap();
    engine.undo().unwrap();
    assert_eq!(engine.document().room_labels[&id], label);
    let before = engine.document().clone();
    let mut invalid = label.clone();
    invalid.id = Id::new_v4();
    invalid.position.x = f64::NAN;
    assert!(engine.execute(Command::CreateRoomLabel(invalid)).is_err());
    assert_eq!(engine.document(), &before);
    engine.execute(Command::DeleteObject { id }).unwrap();
    assert!(engine.document().room_labels.is_empty());
    engine.undo().unwrap();
    assert_eq!(engine.document().room_labels[&id], label);
    assert_eq!(engine.document().walls, walls);
}
