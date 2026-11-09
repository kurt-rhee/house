use super::*;

impl HouseApp {
    pub(super) fn fixture_properties(&mut self, ui: &mut egui::Ui, apply: &mut Option<Command>) {
        if let Some(f) = &mut self.draft_fixture {
            ui.label(format!("{:?} {}", f.kind, f.id));
            for (label, value) in [
                ("X", &mut f.origin.x),
                ("Y", &mut f.origin.y),
                ("Width", &mut f.width),
                ("Depth", &mut f.depth),
                ("Rotation (degrees)", &mut f.rotation),
            ] {
                ui.horizontal(|ui| {
                    ui.label(label);
                    ui.add(egui::DragValue::new(value));
                });
            }
            if ui.button("Apply fixture properties").clicked() {
                *apply = Some(Command::UpdateFixture(f.clone()));
            }
        }
        if let Some(w) = &mut self.draft_window {
            ui.label(format!("Window {}", w.id));
            ui.label(format!("Host {}", w.wall));
            for (label, value) in [("Position", &mut w.position), ("Width", &mut w.width)] {
                ui.horizontal(|ui| {
                    ui.label(label);
                    ui.add(egui::DragValue::new(value));
                });
            }
            if ui.button("Apply window properties").clicked() {
                *apply = Some(Command::UpdateWindow(w.clone()));
            }
        }
    }
    pub(super) fn draw_plan_symbols(&self, d: &Document, painter: &egui::Painter, origin: Pos2) {
        for (wall, position, width) in d
            .windows
            .values()
            .map(|v| (v.wall, v.position, v.width))
            .chain(
                d.doors
                    .values()
                    .filter(|v| v.kind != DoorKind::Hinged)
                    .map(|v| (v.wall, v.position, v.width)),
            )
        {
            let w = &d.walls[&wall];
            if !d.layers[&w.layer].visible {
                continue;
            }
            let l = length(w);
            let p = |station: f64| {
                self.screen(
                    Point::new(
                        w.start.x + (w.end.x - w.start.x) * station / l,
                        w.start.y + (w.end.y - w.start.y) * station / l,
                    ),
                    origin,
                )
            };
            painter.line_segment(
                [p(position - width / 2.0), p(position + width / 2.0)],
                Stroke::new(
                    (w.thickness as f32 + 2.0) * self.scale,
                    Color32::from_rgb(248, 248, 244),
                ),
            );
        }
        for symbol in house_geometry::plan_symbols(d) {
            if !d.layers[&symbol.layer].visible {
                continue;
            }
            let color = if self.selected == Some(symbol.id) {
                Color32::RED
            } else {
                Color32::from_rgb(30, 110, 150)
            };
            for (a, b) in symbol.lines {
                painter.line_segment(
                    [self.screen(a, origin), self.screen(b, origin)],
                    Stroke::new(1.5, color),
                );
            }
        }
        if let Some(kind) = self.placing {
            painter.text(
                painter.clip_rect().left_top() + Vec2::splat(12.0),
                egui::Align2::LEFT_TOP,
                format!("Click to place {kind:?} · Esc cancels"),
                egui::FontId::proportional(14.0),
                Color32::from_rgb(30, 110, 150),
            );
        }
    }
    pub(super) fn pick_fixture_or_window(&self, d: &Document, p: Point) -> Option<Id> {
        d.fixtures
            .values()
            .filter(|f| d.layers[&f.layer].visible)
            .find(|f| house_geometry::fixture_contains(f, p))
            .map(|f| f.id)
            .or_else(|| {
                d.windows
                    .values()
                    .filter(|v| d.layers[&d.walls[&v.wall].layer].visible)
                    .find(|v| {
                        let w = &d.walls[&v.wall];
                        let dx = w.end.x - w.start.x;
                        let dy = w.end.y - w.start.y;
                        let station = ((p.x - w.start.x) * dx + (p.y - w.start.y) * dy) / length(w);
                        (station - v.position).abs() <= v.width / 2.0
                            && distance(w, p) < w.thickness / 2.0 + 8.0 / self.scale as f64
                    })
                    .map(|v| v.id)
            })
    }
}
