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

fn label_position(ctx: &egui::Context, app: &mut HouseApp, label: &str) -> Pos2 {
    let mut output = ctx.run_ui(
        egui::RawInput {
            screen_rect: Some(egui::Rect::from_min_size(
                Pos2::ZERO,
                Vec2::new(1280.0, 850.0),
            )),
            ..Default::default()
        },
        |ui| app.show(ui),
    );
    output.textures_delta.clear();
    output
        .shapes
        .iter()
        .find_map(|clipped| match &clipped.shape {
            egui::Shape::Text(text) if text.galley.text() == label => {
                Some(text.pos + text.galley.rect.center().to_vec2())
            }
            _ => None,
        })
        .expect("comparison tab is visible")
}

#[test]
fn before_after_switch_keeps_the_live_document_and_camera() {
    let ctx = egui::Context::default();
    let mut app = HouseApp::with_context(ctx.clone(), 0);
    app.before_reference = Some(BeforeReference::load(&ctx).expect("reference fits renderer"));
    let before_tab = label_position(&ctx, &mut app, "Before");
    let live = app.handle.snapshot();
    let camera = (app.canvas_origin, app.pan, app.scale);
    click(&ctx, &mut app, before_tab);
    assert!(app.show_before);
    assert_eq!((app.canvas_origin, app.pan, app.scale), camera);
    let after_tab = label_position(&ctx, &mut app, "After");
    click(&ctx, &mut app, after_tab);
    assert!(!app.show_before);
    assert_eq!((app.canvas_origin, app.pan, app.scale), camera);
    assert!(std::sync::Arc::ptr_eq(&live, &app.handle.snapshot()));
}

#[test]
fn switches_between_vector_elevation_and_editable_floor_plan() {
    let ctx = egui::Context::default();
    let mut app = HouseApp::with_context(ctx.clone(), 0);
    let path = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../output/floor-plan.house.json");
    app.open_elevations(&path);
    let elevations = app.elevations.as_ref().expect("saved elevations open");
    assert!(
        elevations
            .drawings
            .iter()
            .any(|drawing| drawing.id.starts_with("I-"))
    );
    let page = elevations
        .drawings
        .iter()
        .position(|drawing| drawing.id == "A-03")
        .expect("exterior elevation is indexed");
    let title = elevations.drawings[page].title.clone();
    let live = app.handle.snapshot();
    let switcher = label_position(&ctx, &mut app, "Elevations");
    click(&ctx, &mut app, switcher);
    let choice = label_position(&ctx, &mut app, &title);
    click(&ctx, &mut app, choice);
    assert_eq!(app.elevation, Some(page));
    assert!(!app.editing_plan());
    let label = label_position(&ctx, &mut app, "North exterior elevation");
    click(&ctx, &mut app, label);
    label_position(&ctx, &mut app, "Save move");
    let after = label_position(&ctx, &mut app, "After");
    click(&ctx, &mut app, after);
    assert!(app.editing_plan());
    assert!(std::sync::Arc::ptr_eq(&live, &app.handle.snapshot()));
}

#[test]
fn toolbar_exports_floor_plan_and_all_elevations_in_one_dxf() {
    use dxf::entities::EntityType;

    let ctx = egui::Context::default();
    let mut app = HouseApp::with_context(ctx.clone(), 0);
    let project = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../output/floor-plan.house.json");
    app.open_elevations(&project);
    let output = std::env::temp_dir().join(format!("house-export-{}", uuid::Uuid::new_v4()));
    std::fs::create_dir(&output).unwrap();
    app.path = output
        .join("floor-plan.house.json")
        .to_string_lossy()
        .into();
    let plan = house_io::plan_dxf_drawing(&app.handle.snapshot()).unwrap();
    let button = label_position(&ctx, &mut app, "Export DXF");
    click(&ctx, &mut app, button);

    let combined = dxf::Drawing::load_file(output.join("floor-plan.combined.dxf")).unwrap();
    std::fs::remove_dir_all(output).unwrap();
    assert_eq!(
        combined.header.default_drawing_units,
        dxf::enums::Units::Millimeters
    );
    let first_wall = plan
        .entities()
        .find_map(|entity| match &entity.specific {
            EntityType::LwPolyline(polyline) => Some((&entity.common.layer, &polyline.vertices)),
            _ => None,
        })
        .unwrap();
    assert!(combined.entities().any(|entity| {
        matches!(&entity.specific, EntityType::LwPolyline(line)
            if &entity.common.layer == first_wall.0
                 && line.vertices.iter().map(|point| (point.x, point.y))
                    .eq(first_wall.1.iter().map(|point| (point.x, point.y))))
    }));
    let mut drawing_bounds = Vec::new();
    for elevation in &app.elevations.as_ref().unwrap().drawings {
        let layer = format!("{}_LINES", elevation.id);
        let bounds = combined
            .entities()
            .filter(|entity| entity.common.layer == layer)
            .fold(kurbo::Rect::ZERO, |bounds, entity| match &entity.specific {
                EntityType::LwPolyline(line) => {
                    line.vertices.iter().fold(bounds, |bounds, point| {
                        let point = kurbo::Point::new(point.x, point.y);
                        if bounds == kurbo::Rect::ZERO {
                            kurbo::Rect::from_points(point, point)
                        } else {
                            bounds.union_pt(point)
                        }
                    })
                }
                _ => bounds,
            });
        assert!(
            bounds.x0 > plan.header.maximum_drawing_extents.x,
            "{}",
            elevation.id
        );
        assert!(
            drawing_bounds
                .iter()
                .all(|other| bounds.intersect(*other).area() == 0.0)
        );
        drawing_bounds.push(bounds);
    }
    assert!(drawing_bounds.len() > 1);
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
        hinge_at_end: false,
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

#[test]
fn renamed_room_is_painted_on_the_live_drawing() {
    let ctx = egui::Context::default();
    let mut app = HouseApp::with_context(ctx.clone(), 0);
    let room = app.handle.snapshot().rooms.values().next().unwrap().id;
    let name = "Guest bathroom";
    app.handle
        .submit(Action::Edit(Command::RenameRoom {
            id: room,
            name: name.into(),
        }))
        .unwrap()
        .blocking_recv()
        .unwrap()
        .unwrap();
    let input = egui::RawInput {
        screen_rect: Some(egui::Rect::from_min_size(
            Pos2::ZERO,
            Vec2::new(1280.0, 850.0),
        )),
        ..Default::default()
    };
    let mut output = ctx.run_ui(input, |ui| app.show(ui));
    output.textures_delta.clear();
    // The canvas paints name + area together; the sidebar uses a different label.
    assert!(output.shapes.iter().any(|s| match &s.shape {
        egui::Shape::Text(text) => text.galley.job.text.starts_with(&format!("{name}\n")),
        _ => false,
    }));
}
