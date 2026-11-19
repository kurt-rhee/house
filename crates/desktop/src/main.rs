mod canvas;
mod elevations;
mod fixtures;
use eframe::egui::{self, Color32, Pos2, Sense, Stroke, Vec2};
use elevations::Elevations;
use house_commands::Command;
use house_core::*;
use house_geometry::{
    ROOM_SIZE_TEXT_HEIGHT, ROOM_SIZE_TEXT_OFFSET, dimension_value, distance, length, room_bounds,
    room_label_size, wall_polygon,
};
use house_mcp::{Action, DocumentHandle, LocalServer, Pending, PendingError};
use std::path::{Path, PathBuf};

struct BeforeReference {
    texture: egui::TextureHandle,
    width_mm: f64,
    height_mm: f64,
}

impl BeforeReference {
    fn load(ctx: &egui::Context) -> image::ImageResult<Self> {
        let mut image = image::load_from_memory_with_format(
            include_bytes!("../../../docs/floor-plan-before-reference.png"),
            image::ImageFormat::Png,
        )?;
        // Approximate scale from the exterior wall centers shared by both plans.
        let mm_per_pixel = 11.44;
        let width_mm = f64::from(image.width()) * mm_per_pixel;
        let height_mm = f64::from(image.height()) * mm_per_pixel;
        let limit = ctx.input(|input| input.max_texture_side) as u32;
        if image.width().max(image.height()) > limit {
            image = image.resize(limit, limit, image::imageops::FilterType::Lanczos3);
        }
        let pixels = image.into_rgba8();
        let size = [pixels.width() as usize, pixels.height() as usize];
        let texture = ctx.load_texture(
            "Existing floor plan",
            egui::ColorImage::from_rgba_unmultiplied(size, pixels.as_raw()),
            egui::TextureOptions::LINEAR,
        );
        Ok(Self {
            texture,
            width_mm,
            height_mm,
        })
    }
}

struct HouseApp {
    handle: DocumentHandle,
    pending: Vec<(Pending, Option<PathBuf>)>,
    server: Result<LocalServer, String>,
    before_reference: Option<BeforeReference>,
    show_before: bool,
    elevations: Option<Elevations>,
    elevation_load_error: Option<String>,
    elevation: Option<usize>,
    scale: f32,
    pan: Vec2,
    selected: Option<Id>,
    drawing: bool,
    placing: Option<FixtureKind>,
    first: Option<Point>,
    drag: Option<(Id, Point)>,
    path: String,
    status: String,
    imperial: bool,
    draft_wall: Option<Wall>,
    draft_door: Option<Door>,
    draft_fixture: Option<Fixture>,
    draft_window: Option<Window>,
    draft_revision: u64,
    move_x: String,
    move_y: String,
    canvas_origin: Pos2,
}
impl HouseApp {
    fn new(cc: &eframe::CreationContext<'_>) -> Self {
        let mut app = Self::with_context(cc.egui_ctx.clone(), 3847);
        match BeforeReference::load(&cc.egui_ctx) {
            Ok(reference) => app.before_reference = Some(reference),
            Err(error) => app.status = format!("Could not load Before plan: {error}"),
        }
        let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("../../output/floor-plan.house.json");
        app.path = path.to_string_lossy().into_owned();
        match app
            .handle
            .submit(Action::Open(path.clone()))
            .and_then(|rx| rx.blocking_recv().map_err(|e| e.to_string())?)
        {
            Ok(_) => {
                app.scale = 0.034;
                app.pan = Vec2::new(20.0, 20.0);
                app.open_elevations(&path);
            }
            Err(error) => app.status = format!("Could not open saved floor plan: {error}"),
        }
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
            before_reference: None,
            show_before: false,
            elevations: None,
            elevation_load_error: None,
            elevation: None,
            scale: 0.22,
            pan: Vec2::new(100.0, 100.0),
            selected: None,
            drawing: false,
            placing: None,
            first: None,
            drag: None,
            path: "bathroom.house.json".into(),
            status: "Ready · preliminary design, not construction documents".into(),
            imperial: false,
            draft_wall: None,
            draft_door: None,
            draft_fixture: None,
            draft_window: None,
            draft_revision: u64::MAX,
            move_x: "6 in".into(),
            move_y: "0".into(),
            canvas_origin: Pos2::ZERO,
        }
    }
    fn send(&mut self, a: Action) {
        let opened = match &a {
            Action::Open(path) => Some(path.clone()),
            _ => None,
        };
        match self.handle.submit(a) {
            Ok(rx) => self.pending.push((rx, opened)),
            Err(e) => self.status = e,
        }
    }
    fn open_elevations(&mut self, project: &Path) {
        self.elevation = None;
        self.elevation_load_error = None;
        self.elevations = match Elevations::open(project) {
            Ok(elevations) => elevations,
            Err(error) => {
                self.status = error.clone();
                self.elevation_load_error = Some(error);
                None
            }
        };
    }
    fn export_project_dxf(&mut self, document: &Document) {
        if let Some(error) = &self.elevation_load_error {
            self.status = format!("DXF export requires the elevation drawings. {error}");
            return;
        }
        let project = Path::new(&self.path);
        if let (Some(elevations), Some(filename)) = (&self.elevations, project.file_name()) {
            let filename = filename.to_string_lossy();
            let stem = filename.strip_suffix(".house.json").unwrap_or(&filename);
            let path = project.with_file_name(format!("{stem}.combined.dxf"));
            self.status = match elevations.export_project(document, &path) {
                Ok(()) => format!(
                    "Exported floor plan and {} elevations to {}",
                    elevations.drawings.len(),
                    path.display()
                ),
                Err(error) => format!("DXF export failed: {error}"),
            };
        } else {
            self.send(Action::ExportDxf(project.with_extension("dxf")));
        }
    }
    fn select_view(&mut self, before: bool, elevation: Option<usize>) {
        self.show_before = before;
        if self.elevation != elevation
            && let Some(elevations) = &mut self.elevations
        {
            elevations.switch_view();
        }
        self.elevation = elevation;
        self.first = None;
        self.drag = None;
        self.placing = None;
        self.drawing = false;
    }
    fn editing_plan(&self) -> bool {
        !self.show_before && self.elevation.is_none()
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
                .or(self.draft_fixture.as_ref().map(|v| v.id))
                .or(self.draft_window.as_ref().map(|v| v.id))
                != self.selected
        {
            self.draft_wall = self.selected.and_then(|id| d.walls.get(&id).cloned());
            self.draft_door = self.selected.and_then(|id| d.doors.get(&id).cloned());
            self.draft_fixture = self.selected.and_then(|id| d.fixtures.get(&id).cloned());
            self.draft_window = self.selected.and_then(|id| d.windows.get(&id).cloned());
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
                ui.selectable_value(&mut v.kind, DoorKind::Hinged, "Hinged");
                ui.selectable_value(&mut v.kind, DoorKind::SlidingGlass, "Sliding glass");
                ui.selectable_value(&mut v.kind, DoorKind::FrenchGlass, "Glass French doors");
                ui.selectable_value(&mut v.kind, DoorKind::Garage, "Garage door");
                ui.selectable_value(&mut v.kind, DoorKind::Pocket, "Pocket door");
                ui.selectable_value(&mut v.kind, DoorKind::RoundedArch, "Rounded arch (no door)");
            });
            ui.horizontal(|ui| {
                ui.selectable_value(&mut v.swing, Swing::Left, "Left");
                ui.selectable_value(&mut v.swing, Swing::Right, "Right");
            });
            ui.checkbox(&mut v.hinge_at_end, "Hinge at opposite jamb");
            if ui.button("Apply door properties").clicked() {
                apply = Some(Command::UpdateDoor(v.clone()));
            }
        }
        self.fixture_properties(ui, &mut apply);
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
                        hinge_at_end: false,
                        id: Id::new_v4(),
                        wall: id,
                        position: length(w) / 2.0,
                        width: inches(28.0),
                        kind: house_core::DoorKind::Hinged,
                        swing: Swing::Left,
                    }));
                }
            }
            if let Some(w) = d.walls.get(&id) {
                if ui.button("Add centered 36 in window").clicked() {
                    self.edit(Command::CreateWindow(Window {
                        id: Id::new_v4(),
                        wall: id,
                        position: length(w) / 2.0,
                        width: inches(36.0),
                    }));
                }
                if ui.button("Add centered 60 in sliding glass door").clicked() {
                    self.edit(Command::CreateDoor(Door {
                        hinge_at_end: false,
                        id: Id::new_v4(),
                        wall: id,
                        position: length(w) / 2.0,
                        width: inches(60.0),
                        swing: Swing::Left,
                        kind: DoorKind::SlidingGlass,
                    }));
                }
            }
            if ui.button("Delete selected").clicked() {
                self.edit(Command::DeleteObject { id });
            }
        } else {
            ui.label("Click a wall, opening or fixture to select.");
        }
        ui.separator();
        ui.heading("Rooms");
        for label in d.room_labels.values() {
            if let Some(size) = room_label_size(d, label) {
                ui.label(format!("{}\n{}", label.name, size.text));
            } else {
                ui.label(&label.name);
            }
        }
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
        let mut opened_project = None;
        self.pending.retain_mut(|(rx, opened)| match rx.try_recv() {
            Ok(r) => {
                self.status = match r {
                    Ok(v) => {
                        if let Some(path) = opened.take() {
                            opened_project = Some(path);
                        }
                        v.to_string()
                    }
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
        if let Some(project) = opened_project {
            self.select_view(false, None);
            self.selected = None;
            self.open_elevations(&project);
        }
        let ctx = ui.ctx().clone();
        if self.editing_plan()
            && ctx.input_mut(|i| {
                i.consume_key(
                    egui::Modifiers::COMMAND | egui::Modifiers::SHIFT,
                    egui::Key::Z,
                )
            })
        {
            self.send(Action::Redo);
        }
        if self.editing_plan()
            && ctx.input_mut(|i| i.consume_key(egui::Modifiers::COMMAND, egui::Key::Z))
        {
            self.send(Action::Undo);
        }
        if ctx.input(|i| i.key_pressed(egui::Key::Escape)) {
            self.first = None;
            self.placing = None;
            self.drawing = false;
        }
        let d = self.handle.snapshot();
        egui::Panel::top("toolbar").show(ui, |ui| {
            ui.horizontal(|ui| {
                ui.heading("House");
                if self.before_reference.is_some() {
                    if ui.selectable_label(self.show_before, "Before").clicked() {
                        self.select_view(true, None);
                    }
                }
                if ui.selectable_label(self.editing_plan(), "After").clicked()
                    && !self.editing_plan()
                {
                    self.select_view(false, None);
                }
                if let Some(elevations) = &self.elevations {
                    let label = self.elevation.map_or("Elevations", |index| {
                        elevations.drawings[index].title.as_str()
                    });
                    let mut selected = self.elevation;
                    egui::ComboBox::from_id_salt("elevation drawings")
                        .selected_text(label)
                        .height(460.0)
                        .show_ui(ui, |ui| {
                            let mut section = None;
                            for (index, drawing) in elevations.drawings.iter().enumerate() {
                                let exterior = drawing.id.starts_with("A-");
                                if section != Some(exterior) {
                                    section = Some(exterior);
                                    ui.separator();
                                    ui.strong(if exterior { "Exterior" } else { "Interior" });
                                }
                                ui.selectable_value(&mut selected, Some(index), &drawing.title);
                            }
                        });
                    if selected != self.elevation {
                        self.select_view(false, selected);
                    }
                }
                if self.elevation.is_some() {
                    ui.label("Elevation drawing");
                } else if self.show_before {
                    ui.label("Existing conditions · reference drawing");
                } else {
                    ui.label(format!("rev {}", d.revision));
                }
                if ui
                    .button("Export DXF")
                    .on_hover_text("Export the floor plan and all elevation drawings")
                    .clicked()
                {
                    self.export_project_dxf(&d);
                }
            });
            ui.horizontal_wrapped(|ui| {
                if !self.editing_plan() {
                    ui.disable();
                }
                if ui
                    .selectable_label(!self.drawing && self.placing.is_none(), "Select")
                    .clicked()
                {
                    self.placing = None;
                    self.drawing = false;
                    self.first = None;
                }
                if ui.selectable_label(self.drawing, "Draw wall").clicked() {
                    self.placing = None;
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
                if ui.button("Place bath").clicked() {
                    self.placing = Some(FixtureKind::Bath);
                    self.drawing = false;
                    self.first = None;
                }
                if ui.button("Place shower").clicked() {
                    self.placing = Some(FixtureKind::Shower);
                    self.drawing = false;
                    self.first = None;
                }
                if ui.button("SVG").clicked() {
                    self.send(Action::Export(
                        std::path::Path::new(&self.path).with_extension("svg"),
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
                if let (Some(index), Some(elevations)) = (self.elevation, &mut self.elevations) {
                    elevations.inspector(ui, index, &mut self.status);
                } else if self.show_before {
                    ui.heading("Before");
                    ui.label("Pan with middle or right drag. Scroll to zoom.");
                } else {
                    egui::ScrollArea::vertical().show(ui, |ui| self.inspector(ui, &d));
                }
            });
        egui::CentralPanel::default().show(ui, |ui| {
            if let (Some(index), Some(elevations)) = (self.elevation, &mut self.elevations) {
                elevations.show(ui, index);
            } else if self.show_before {
                self.before_canvas(ui);
            } else {
                self.canvas(ui, &d);
            }
        });
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
