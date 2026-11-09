mod canvas;
use eframe::egui::{self, Color32, Pos2, Sense, Stroke, Vec2};
use house_commands::Command;
use house_core::*;
use house_geometry::{dimension_value, distance, length, room_bounds, wall_polygon};
use house_mcp::{Action, DocumentHandle, LocalServer, Pending, PendingError};
struct HouseApp {
    handle: DocumentHandle,
    pending: Vec<Pending>,
    server: Result<LocalServer, String>,
    scale: f32,
    pan: Vec2,
    selected: Option<Id>,
    drawing: bool,
    first: Option<Point>,
    drag: Option<(Id, Point)>,
    path: String,
    status: String,
    imperial: bool,
    draft_wall: Option<Wall>,
    draft_door: Option<Door>,
    draft_revision: u64,
    move_x: String,
    move_y: String,
    canvas_origin: Pos2,
}
impl HouseApp {
    fn new(cc: &eframe::CreationContext<'_>) -> Self {
        let mut app = Self::with_context(cc.egui_ctx.clone(), 3847);
        if let Ok(server) = &mut app.server {
            let result = std::env::var_os("HOME")
                .ok_or("Home directory is unavailable".to_string())
                .and_then(|home| {
                    server.publish_connection(
                        std::path::PathBuf::from(home)
                            .join("Library/Application Support/House/mcp.json"),
                    )
                });
            if let Err(error) = result {
                app.status = format!("Agent connection file failed: {error}");
            }
        }
        app
    }
    fn with_context(ctx: egui::Context, mcp_port: u16) -> Self {
        let handle =
            DocumentHandle::spawn(bathroom(), move || ctx.request_repaint()).expect("valid sample");
        let server = house_mcp::start_local(handle.clone(), mcp_port);
        match &server {
            Ok(server) => eprintln!(
                "MCP http://{}/mcp  Authorization: Bearer {}",
                server.address, server.token
            ),
            Err(error) => eprintln!("MCP startup failed: {error}"),
        }
        Self {
            handle,
            pending: vec![],
            server,
            scale: 0.22,
            pan: Vec2::new(100.0, 100.0),
            selected: None,
            drawing: false,
            first: None,
            drag: None,
            path: "bathroom.house.json".into(),
            status: "Ready · preliminary design, not construction documents".into(),
            imperial: false,
            draft_wall: None,
            draft_door: None,
            draft_revision: u64::MAX,
            move_x: "6 in".into(),
            move_y: "0".into(),
            canvas_origin: Pos2::ZERO,
        }
    }
    fn send(&mut self, a: Action) {
        match self.handle.submit(a) {
            Ok(rx) => self.pending.push(rx),
            Err(e) => self.status = e,
        }
    }
    fn edit(&mut self, c: Command) {
        self.send(Action::Edit(c))
    }
    fn apply_properties(&mut self, command: Command) {
        self.send(Action::EditAtRevision {
            command,
            expected_revision: self.draft_revision,
        });
    }
    fn display(&self, mm: f64) -> String {
        if self.imperial {
            format!("{:.3} in", mm / 25.4)
        } else {
            format!("{mm:.1} mm")
        }
    }
    fn screen(&self, p: Point, origin: Pos2) -> Pos2 {
        origin + self.pan + Vec2::new(p.x as f32, p.y as f32) * self.scale
    }
    fn world(&self, p: Pos2, origin: Pos2) -> Point {
        let v = (p - origin - self.pan) / self.scale;
        Point::new(v.x as f64, v.y as f64)
    }
    fn snap(p: Point) -> Point {
        let g = 25.4;
        Point::new((p.x / g).round() * g, (p.y / g).round() * g)
    }
    fn inspector(&mut self, ui: &mut egui::Ui, d: &Document) {
        ui.heading("Properties");
        ui.checkbox(&mut self.imperial, "Display inches");
        ui.label("Property inputs: mm (or use Move by below)");
        if self.draft_revision != d.revision
            || self
                .draft_wall
                .as_ref()
                .map(|w| w.id)
                .or(self.draft_door.as_ref().map(|v| v.id))
                != self.selected
        {
            self.draft_wall = self.selected.and_then(|id| d.walls.get(&id).cloned());
            self.draft_door = self.selected.and_then(|id| d.doors.get(&id).cloned());
            self.draft_revision = d.revision;
        }
        let mut apply = None;
        if let Some(w) = &mut self.draft_wall {
            ui.label(format!("Wall {}", w.id));
            ui.text_edit_singleline(&mut w.name);
            for (label, v) in [
                ("Start X", &mut w.start.x),
                ("Start Y", &mut w.start.y),
                ("End X", &mut w.end.x),
                ("End Y", &mut w.end.y),
                ("Thickness", &mut w.thickness),
            ] {
                ui.horizontal(|ui| {
                    ui.label(label);
                    ui.add(egui::DragValue::new(v).speed(1.0));
                });
            }
            if ui.button("Apply wall properties").clicked() {
                apply = Some(Command::UpdateWall(w.clone()));
            }
        }
        if let Some(v) = &mut self.draft_door {
            ui.label(format!("Door {}", v.id));
            ui.label(format!("Host {}", v.wall));
            ui.horizontal(|ui| {
                ui.label("Position");
                ui.add(egui::DragValue::new(&mut v.position));
            });
            ui.horizontal(|ui| {
                ui.label("Width");
                ui.add(egui::DragValue::new(&mut v.width));
            });
            ui.horizontal(|ui| {
                ui.selectable_value(&mut v.swing, Swing::Left, "Left");
                ui.selectable_value(&mut v.swing, Swing::Right, "Right");
            });
            if ui.button("Apply door properties").clicked() {
                apply = Some(Command::UpdateDoor(v.clone()));
            }
        }
        if let Some(command) = apply {
            self.apply_properties(command);
        }
        if let Some(id) = self.selected {
            if d.walls.contains_key(&id) {
                ui.separator();
                ui.label("Move wall by (mm, in, ft, or 11' 2\")");
                ui.horizontal(|ui| {
                    ui.label("dx");
                    ui.text_edit_singleline(&mut self.move_x);
                });
                ui.horizontal(|ui| {
                    ui.label("dy");
                    ui.text_edit_singleline(&mut self.move_y);
                });
                if ui.button("Move by entered offset").clicked() {
                    match (parse_length(&self.move_x), parse_length(&self.move_y)) {
                        (Ok(dx), Ok(dy)) => self.edit(Command::MoveWall { id, dx, dy }),
                        _ => self.status = "Invalid length".into(),
                    }
                }

                ui.horizontal(|ui| {
                    if ui.button("← 6 in").clicked() {
                        self.edit(Command::MoveWall {
                            id,
                            dx: -inches(6.0),
                            dy: 0.0,
                        });
                    }
                    if ui.button("6 in →").clicked() {
                        self.edit(Command::MoveWall {
                            id,
                            dx: inches(6.0),
                            dy: 0.0,
                        });
                    }
                });
                if ui.button("Add centered 28 in door").clicked() {
                    let w = &d.walls[&id];
                    self.edit(Command::CreateDoor(Door {
                        id: Id::new_v4(),
                        wall: id,
                        position: length(w) / 2.0,
                        width: inches(28.0),
                        swing: Swing::Left,
                    }));
                }
            }
            if ui.button("Delete selected").clicked() {
                self.edit(Command::DeleteObject { id });
            }
        } else {
            ui.label("Click a wall or door to select.");
        }
        ui.separator();
        ui.heading("Rooms");
        for r in d.rooms.values() {
            if let Ok(b) = room_bounds(d, r) {
                ui.label(format!(
                    "{}\n{} × {}\n{:.3} m²",
                    r.name,
                    self.display(b.width),
                    self.display(b.height),
                    b.area() / 1e6
                ));
            }
        }
        ui.separator();
        ui.label("Pan: middle/right drag\nZoom: scroll at pointer\nDraw wall: click two grid points\nMove: drag a selected wall\nGrid snap: 1 inch\nUndo: ⌘Z / redo: ⌘⇧Z");
    }
}
impl HouseApp {
    fn show(&mut self, ui: &mut egui::Ui) {
        self.pending.retain_mut(|rx| match rx.try_recv() {
            Ok(r) => {
                self.status = match r {
                    Ok(v) => v.to_string(),
                    Err(e) => format!("Rejected: {e}"),
                };
                false
            }
            Err(PendingError::Closed) => {
                self.status = "Document worker disconnected".into();
                false
            }
            Err(_) => true,
        });
        let ctx = ui.ctx().clone();
        if ctx.input_mut(|i| {
            i.consume_key(
                egui::Modifiers::COMMAND | egui::Modifiers::SHIFT,
                egui::Key::Z,
            )
        }) {
            self.send(Action::Redo);
        }
        if ctx.input_mut(|i| i.consume_key(egui::Modifiers::COMMAND, egui::Key::Z)) {
            self.send(Action::Undo);
        }
        if ctx.input(|i| i.key_pressed(egui::Key::Escape)) {
            self.first = None;
            self.drawing = false;
        }
        let d = self.handle.snapshot();
        egui::Panel::top("toolbar").show(ui, |ui| {
            ui.horizontal_wrapped(|ui| {
                ui.heading("House");
                ui.label(format!("rev {}", d.revision));
                if ui.selectable_label(!self.drawing, "Select").clicked() {
                    self.drawing = false;
                    self.first = None;
                }
                if ui.selectable_label(self.drawing, "Draw wall").clicked() {
                    self.drawing = true;
                }
                if ui.button("Undo").clicked() {
                    self.send(Action::Undo);
                }
                if ui.button("Redo").clicked() {
                    self.send(Action::Redo);
                }
                if ui.button("Fit sample").clicked() {
                    self.scale = 0.22;
                    self.pan = Vec2::new(100.0, 100.0);
                }
                ui.text_edit_singleline(&mut self.path);
                if ui.button("Open").clicked() {
                    self.send(Action::Open(self.path.clone().into()));
                }
                if ui.button("Save").clicked() {
                    self.send(Action::Save(self.path.clone().into()));
                }
                if ui.button("SVG").clicked() {
                    self.send(Action::Export(
                        std::path::Path::new(&self.path).with_extension("svg"),
                    ));
                }
                if ui.button("DXF").clicked() {
                    self.send(Action::ExportDxf(
                        std::path::Path::new(&self.path).with_extension("dxf"),
                    ));
                }
            });
            ui.horizontal(|ui| {
                match &self.server {
                    Ok(server) => {
                        ui.label(format!("MCP http://{}/mcp", server.address));
                        if ui.button("Copy token").clicked() {
                            ctx.copy_text(server.token.clone());
                        }
                    }
                    Err(error) => {
                        ui.colored_label(Color32::RED, format!("MCP startup failed: {error}"));
                    }
                }
                ui.label(&self.status);
            });
        });
        egui::Panel::right("inspector")
            .default_size(260.0)
            .show(ui, |ui| {
                egui::ScrollArea::vertical().show(ui, |ui| self.inspector(ui, &d));
            });
        egui::CentralPanel::default().show(ui, |ui| self.canvas(ui, &d));
    }
}
impl eframe::App for HouseApp {
    fn ui(&mut self, ui: &mut egui::Ui, _frame: &mut eframe::Frame) {
        self.show(ui);
    }
}

fn main() -> eframe::Result {
    eframe::run_native(
        "House · Architectural Drafting",
        eframe::NativeOptions {
            viewport: egui::ViewportBuilder::default().with_inner_size([1280.0, 850.0]),
            ..Default::default()
        },
        Box::new(|cc| Ok(Box::new(HouseApp::new(cc)))),
    )
}

#[cfg(test)]
mod tests;
