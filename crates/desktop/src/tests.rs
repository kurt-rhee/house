use super::*;
fn frame(ctx: &egui::Context, app: &mut HouseApp, events: Vec<egui::Event>) {
    let input = egui::RawInput {
        screen_rect: Some(egui::Rect::from_min_size(
            Pos2::ZERO,
            Vec2::new(1280.0, 850.0),
        )),
        events,
        ..Default::default()
    };
    let mut out = ctx.run_ui(input, |ui| app.show(ui));
    out.textures_delta.clear();
    assert!(out.shapes.len() > 10);
}
fn button(p: Pos2, pressed: bool) -> egui::Event {
    egui::Event::PointerButton {
        pos: p,
        button: egui::PointerButton::Primary,
        pressed,
        modifiers: Default::default(),
    }
}
fn click(ctx: &egui::Context, app: &mut HouseApp, p: Pos2) {
    frame(
        ctx,
        app,
        vec![egui::Event::PointerMoved(p), button(p, true)],
    );
    frame(ctx, app, vec![button(p, false)]);
}
fn barrier(app: &HouseApp) {
    app.handle
        .submit(Action::Read)
        .unwrap()
        .blocking_recv()
        .unwrap()
        .unwrap();
}
#[test]
fn select_drag_partition_and_undo() {
    let ctx = egui::Context::default();
    let mut app = HouseApp::with_context(ctx.clone(), 0);
    frame(&ctx, &mut app, vec![]);
    let original = app.handle.snapshot();
    let w = original
        .walls
        .values()
        .find(|w| w.name == "Partition")
        .unwrap();
    let p = app.screen(Point::new(w.start.x, 1000.0), app.canvas_origin);
    click(&ctx, &mut app, p);
    assert_eq!(app.selected, Some(w.id));
    let end = p + Vec2::new(152.4 * app.scale, 0.0);
    frame(&ctx, &mut app, vec![button(p, true)]);
    frame(&ctx, &mut app, vec![egui::Event::PointerMoved(end)]);
    frame(&ctx, &mut app, vec![button(end, false)]);
    barrier(&app);
    let moved = app.handle.snapshot();
    assert_eq!(moved.revision, 1);
    assert!((moved.walls[&w.id].start.x - w.start.x - 152.4).abs() < 1e-9);
    app.handle
        .submit(Action::Undo)
        .unwrap()
        .blocking_recv()
        .unwrap()
        .unwrap();
    let mut restored = (*app.handle.snapshot()).clone();
    restored.revision = 0;
    assert_eq!(restored, *original);
    frame(&ctx, &mut app, vec![]);
}
#[test]
fn draw_wall_and_zoom_at_pointer() {
    let ctx = egui::Context::default();
    let mut app = HouseApp::with_context(ctx.clone(), 0);
    frame(&ctx, &mut app, vec![]);
    let before = app.handle.snapshot();
    app.drawing = true;
    let a = app.screen(Point::new(0.0, 2800.0), app.canvas_origin);
    let b = app.screen(Point::new(1000.0, 2800.0), app.canvas_origin);
    click(&ctx, &mut app, a);
    assert!(app.first.is_some());
    click(&ctx, &mut app, b);
    barrier(&app);
    let after = app.handle.snapshot();
    assert_eq!(after.walls.len(), before.walls.len() + 1);
    let wall = after
        .walls
        .values()
        .find(|w| !before.walls.contains_key(&w.id))
        .unwrap();
    assert_eq!(wall.start, HouseApp::snap(Point::new(0.0, 2800.0)));
    assert_eq!(wall.end, HouseApp::snap(Point::new(1000.0, 2800.0)));
    let p = Pos2::new(400.0, 400.0);
    let at = app.world(p, app.canvas_origin);
    let scale = app.scale;
    frame(
        &ctx,
        &mut app,
        vec![
            egui::Event::PointerMoved(p),
            egui::Event::MouseWheel {
                unit: egui::MouseWheelUnit::Point,
                phase: egui::TouchPhase::Move,
                source: egui::MouseWheelSource::Unknown,
                delta: Vec2::new(0.0, 60.0),
                modifiers: Default::default(),
            },
        ],
    );
    assert!(app.scale > scale);
    let now = app.world(p, app.canvas_origin);
    assert!((now.x - at.x).abs() < 0.001 && (now.y - at.y).abs() < 0.001);
}

#[test]
fn pan_changes_camera_only_and_mcp_starts_automatically() {
    let ctx = egui::Context::default();
    let mut app = HouseApp::with_context(ctx.clone(), 0);
    let server = app.server.as_ref().expect("MCP starts with the app");
    assert!(server.address.ip().is_loopback());
    assert!(std::net::TcpStream::connect(server.address).is_ok());
    frame(&ctx, &mut app, vec![]);
    let original = app.handle.snapshot();
    let pan = app.pan;
    let start = Pos2::new(400.0, 400.0);
    let end = start + Vec2::new(45.0, 30.0);
    let middle = |pos, pressed| egui::Event::PointerButton {
        pos,
        button: egui::PointerButton::Middle,
        pressed,
        modifiers: Default::default(),
    };
    frame(
        &ctx,
        &mut app,
        vec![egui::Event::PointerMoved(start), middle(start, true)],
    );
    frame(&ctx, &mut app, vec![egui::Event::PointerMoved(end)]);
    frame(&ctx, &mut app, vec![middle(end, false)]);
    assert_eq!(app.pan, pan + Vec2::new(45.0, 30.0));
    assert_eq!(*app.handle.snapshot(), *original);
}

#[test]
fn stale_inspector_apply_cannot_overwrite_a_remote_wall_move() {
    let ctx = egui::Context::default();
    let mut app = HouseApp::with_context(ctx.clone(), 0);
    let before = app.handle.snapshot();
    let mut proposal = before
        .walls
        .values()
        .find(|w| w.name == "Partition")
        .unwrap()
        .clone();
    app.selected = Some(proposal.id);
    frame(&ctx, &mut app, vec![]);
    assert_eq!(app.draft_revision, 0);
    app.handle
        .submit(Action::Edit(Command::MoveWall {
            id: proposal.id,
            dx: 152.4,
            dy: 0.0,
        }))
        .unwrap()
        .blocking_recv()
        .unwrap()
        .unwrap();
    let moved = app.handle.snapshot();
    proposal.name = "A stale name change".into();
    app.apply_properties(Command::UpdateWall(proposal));
    barrier(&app);
    frame(&ctx, &mut app, vec![]);
    assert_eq!(*app.handle.snapshot(), *moved);
    assert!(app.status.contains("Revision conflict"), "{}", app.status);
    assert_eq!(app.draft_revision, 1);
    assert_eq!(
        app.draft_wall.as_ref().unwrap().start,
        moved.walls[&app.selected.unwrap()].start
    );
}

#[test]
fn place_select_and_edit_bath_and_shower() {
    let ctx = egui::Context::default();
    let mut app = HouseApp::with_context(ctx.clone(), 0);
    frame(&ctx, &mut app, vec![]);
    for (kind, x) in [(FixtureKind::Bath, 300.0), (FixtureKind::Shower, 2100.0)] {
        app.placing = Some(kind);
        let origin = Point::new(x, 1700.0);
        let p = app.screen(origin, app.canvas_origin);
        click(&ctx, &mut app, p);
        barrier(&app);
        let d = app.handle.snapshot();
        let f = d
            .fixtures
            .values()
            .find(|v| v.kind == kind)
            .unwrap()
            .clone();
        assert_eq!(f.origin, HouseApp::snap(origin));
        assert_eq!(app.selected, Some(f.id));
        assert!(app.placing.is_none());
        let p = app.screen(
            Point::new(f.origin.x + 100.0, f.origin.y + 100.0),
            app.canvas_origin,
        );
        click(&ctx, &mut app, p);
        assert_eq!(app.selected, Some(f.id));
        frame(&ctx, &mut app, vec![]);
        let mut edited = app.draft_fixture.clone().unwrap();
        edited.origin.x += 152.4;
        edited.rotation = 90.0;
        app.apply_properties(Command::UpdateFixture(edited.clone()));
        barrier(&app);
        assert_eq!(app.handle.snapshot().fixtures[&f.id], edited);
        app.send(Action::Undo);
        barrier(&app);
        assert_eq!(app.handle.snapshot().fixtures[&f.id], f);
    }
}

#[test]
fn select_window_and_sliding_glass_door() {
    let ctx = egui::Context::default();
    let mut app = HouseApp::with_context(ctx.clone(), 0);
    let d = app.handle.snapshot();
    let host = d.walls.values().find(|w| w.name == "South").unwrap();
    let window = Window {
        id: Id::new_v4(),
        wall: host.id,
        position: 600.0,
        width: 600.0,
    };
    let door = Door {
        id: Id::new_v4(),
        wall: host.id,
        position: 2400.0,
        width: 1200.0,
        swing: Swing::Left,
        kind: DoorKind::SlidingGlass,
    };
    app.edit(Command::CreateWindow(window.clone()));
    app.edit(Command::CreateDoor(door.clone()));
    barrier(&app);
    frame(&ctx, &mut app, vec![]);
    for (id, station) in [(window.id, window.position), (door.id, door.position)] {
        let p = app.screen(
            Point::new(host.start.x + station, host.start.y),
            app.canvas_origin,
        );
        click(&ctx, &mut app, p);
        assert_eq!(app.selected, Some(id));
        frame(&ctx, &mut app, vec![]);
    }
    assert_eq!(
        app.draft_door.as_ref().unwrap().kind,
        DoorKind::SlidingGlass
    );
}
