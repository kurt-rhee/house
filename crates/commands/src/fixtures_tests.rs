use super::*;

#[test]
fn bath_and_shower_create_transform_delete_and_exact_history() {
    for kind in [FixtureKind::Bath, FixtureKind::Shower] {
        let mut e = Engine::new(Document::default()).unwrap();
        let layer = *e.document().layers.keys().next().unwrap();
        let mut f = Fixture {
            id: Id::new_v4(),
            kind,
            origin: Point::new(25.4, 50.8),
            width: 1524.0,
            depth: 762.0,
            rotation: 0.0,
            layer,
        };
        e.execute(Command::CreateFixture(f.clone())).unwrap();
        let created = e.document().clone();
        f.origin.x += 152.4;
        f.origin.y -= 25.4;
        f.width = 1600.0;
        f.depth = 800.0;
        f.rotation = 90.0;
        e.execute(Command::UpdateFixture(f.clone())).unwrap();
        assert_eq!(e.document().fixtures[&f.id], f);
        let corners = house_geometry::fixture_corners(&f);
        assert!((corners[1].x - f.origin.x).abs() < 1e-9);
        assert!((corners[1].y - f.origin.y - 1600.0).abs() < 1e-9);
        assert!((corners[2].x - f.origin.x + 800.0).abs() < 1e-9);
        e.undo().unwrap();
        let mut restored = e.document().clone();
        restored.revision = created.revision;
        assert_eq!(restored, created);
        e.redo().unwrap();
        assert_eq!(e.document().fixtures[&f.id], f);
        let valid = e.document().clone();
        for field in 0..6 {
            let mut bad = f.clone();
            match field {
                0 => bad.width = 0.0,
                1 => bad.depth = -1.0,
                2 => bad.rotation = f64::NAN,
                3 => bad.origin.x = f64::INFINITY,
                4 => bad.layer = Id::new_v4(),
                _ => bad.origin.y = 1e10,
            }
            assert!(e.execute(Command::UpdateFixture(bad)).is_err());
            assert_eq!(*e.document(), valid);
        }
        e.execute(Command::DeleteObject { id: f.id }).unwrap();
        assert!(e.document().fixtures.is_empty());
        e.undo().unwrap();
        assert_eq!(e.document().fixtures[&f.id], f);
    }
}

#[test]
fn windows_and_sliding_doors_follow_host_resize_and_reject_overlap_atomically() {
    let mut e = Engine::new(Document::default()).unwrap();
    let wall = Wall {
        id: Id::new_v4(),
        name: "Host".into(),
        start: Point::new(0.0, 0.0),
        end: Point::new(4000.0, 0.0),
        thickness: 100.0,
        layer: *e.document().layers.keys().next().unwrap(),
    };
    e.execute(Command::CreateWall(wall.clone())).unwrap();
    let mut window = Window {
        id: Id::new_v4(),
        wall: wall.id,
        position: 800.0,
        width: 600.0,
    };
    e.execute(Command::CreateWindow(window.clone())).unwrap();
    let door = Door {
        id: Id::new_v4(),
        wall: wall.id,
        position: 2500.0,
        width: 1200.0,
        swing: Swing::Left,
        kind: DoorKind::SlidingGlass,
    };
    e.execute(Command::CreateDoor(door.clone())).unwrap();
    window.position = 1000.0;
    window.width = 700.0;
    e.execute(Command::UpdateWindow(window.clone())).unwrap();
    let before = e.document().clone();
    let mut bad = window.clone();
    bad.position = 2500.0;
    assert!(e.execute(Command::UpdateWindow(bad)).is_err());
    assert_eq!(*e.document(), before);
    assert!(e.execute(Command::DeleteObject { id: wall.id }).is_err());
    e.execute(Command::MoveWall {
        id: wall.id,
        dx: 152.4,
        dy: 100.0,
    })
    .unwrap();
    assert_eq!(e.document().windows[&window.id], window);
    assert_eq!(e.document().doors[&door.id], door);
    let mut resized = e.document().walls[&wall.id].clone();
    resized.end.x += 4000.0;
    e.execute(Command::UpdateWall(resized)).unwrap();
    assert!((e.document().windows[&window.id].position - 2000.0).abs() < 1e-9);
    assert!((e.document().doors[&door.id].position - 5000.0).abs() < 1e-9);
    e.undo().unwrap();
    e.undo().unwrap();
    let mut restored = e.document().clone();
    restored.revision = before.revision;
    assert_eq!(restored, before);
    e.execute(Command::DeleteObject { id: window.id }).unwrap();
    e.undo().unwrap();
    assert_eq!(e.document().windows[&window.id], window);
    let valid = e.document().clone();
    window.position = -1.0;
    assert!(e.execute(Command::UpdateWindow(window)).is_err());
    assert_eq!(*e.document(), valid);
}
