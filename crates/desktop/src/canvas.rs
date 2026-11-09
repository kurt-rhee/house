use super::*;

impl HouseApp {
    pub(super) fn canvas(&mut self, ui: &mut egui::Ui, d: &Document) {
        let (response, painter) = ui.allocate_painter(ui.available_size(), Sense::click_and_drag());
        let rect = response.rect;
        let origin = rect.min;
        self.canvas_origin = origin;
        painter.rect_filled(rect, 0.0, Color32::from_rgb(248, 248, 244));
        if response.hovered() {
            let scroll = ui.input(|i| i.smooth_scroll_delta.y);
            if scroll != 0.0
                && let Some(p) = ui.input(|i| i.pointer.hover_pos())
            {
                let before = self.world(p, origin);
                self.scale = (self.scale * (scroll * 0.002).exp()).clamp(0.01, 5.0);
                self.pan = p - origin - Vec2::new(before.x as f32, before.y as f32) * self.scale;
            }
        }
        if response.dragged_by(egui::PointerButton::Middle)
            || response.dragged_by(egui::PointerButton::Secondary)
        {
            self.pan += ui.input(|i| i.pointer.delta());
        }
        let low = self.world(rect.min, origin);
        let high = self.world(rect.max, origin);
        let grid = if self.scale > 0.15 { 254.0 } else { 1000.0 };
        for x in (low.x / grid).floor() as i64..=(high.x / grid).ceil() as i64 {
            let a = self.screen(Point::new(x as f64 * grid, low.y), origin);
            let b = self.screen(Point::new(x as f64 * grid, high.y), origin);
            painter.line_segment([a, b], Stroke::new(1.0, Color32::from_gray(225)));
        }
        for y in (low.y / grid).floor() as i64..=(high.y / grid).ceil() as i64 {
            let a = self.screen(Point::new(low.x, y as f64 * grid), origin);
            let b = self.screen(Point::new(high.x, y as f64 * grid), origin);
            painter.line_segment([a, b], Stroke::new(1.0, Color32::from_gray(225)));
        }
        for w in d.walls.values().filter(|w| d.layers[&w.layer].visible) {
            let selected = self.selected == Some(w.id);
            let color = if selected {
                Color32::from_rgb(210, 120, 40)
            } else {
                Color32::from_gray(65)
            };
            painter.add(egui::Shape::convex_polygon(
                wall_polygon(w)
                    .iter()
                    .map(|p| self.screen(*p, origin))
                    .collect(),
                color,
                Stroke::NONE,
            ));
        }
        for door in d.doors.values().filter(|v| v.kind == DoorKind::Hinged) {
            let w = &d.walls[&door.wall];
            if !d.layers[&w.layer].visible {
                continue;
            }
            let l = length(w);
            let ux = (w.end.x - w.start.x) / l;
            let uy = (w.end.y - w.start.y) / l;
            let hinge = Point::new(
                w.start.x + ux * (door.position - door.width / 2.0),
                w.start.y + uy * (door.position - door.width / 2.0),
            );
            let point = |x: f64, y: f64| {
                self.screen(
                    Point::new(hinge.x + ux * x - uy * y, hinge.y + uy * x + ux * y),
                    origin,
                )
            };
            painter.line_segment(
                [point(0.0, 0.0), point(door.width, 0.0)],
                Stroke::new(
                    (w.thickness as f32 + 2.0) * self.scale,
                    Color32::from_rgb(248, 248, 244),
                ),
            );
            let sign = if door.swing == Swing::Left { 1.0 } else { -1.0 };
            let color = if self.selected == Some(door.id) {
                Color32::RED
            } else {
                Color32::from_rgb(30, 110, 150)
            };
            painter.line_segment(
                [point(0.0, 0.0), point(0.0, door.width * sign)],
                Stroke::new(1.5, color),
            );
            let arc = (0..=24)
                .map(|i| {
                    let a = i as f64 / 24.0 * std::f64::consts::FRAC_PI_2;
                    point(a.cos() * door.width, a.sin() * door.width * sign)
                })
                .collect();
            painter.add(egui::Shape::line(arc, Stroke::new(1.0, color)));
        }
        self.draw_plan_symbols(d, &painter, origin);
        for label in d.room_labels.values() {
            painter.text(
                self.screen(label.position, origin),
                egui::Align2::CENTER_CENTER,
                &label.name,
                egui::FontId::proportional((220.0 * self.scale).clamp(6.0, 14.0)),
                Color32::from_gray(45),
            );
        }
        for r in d.rooms.values() {
            if let Ok(b) = room_bounds(d, r) {
                painter.text(
                    self.screen(
                        Point::new(b.x + b.width / 2.0, b.y + b.height / 2.0),
                        origin,
                    ),
                    egui::Align2::CENTER_CENTER,
                    format!("{}\n{:.2} m²", r.name, b.area() / 1e6),
                    egui::FontId::proportional(14.0),
                    Color32::from_gray(45),
                );
            }
        }
        for dim in d.dimensions.values() {
            if let (Some(r), Ok(value)) = (d.rooms.get(&dim.room), dimension_value(d, dim)) {
                let b = room_bounds(d, r).unwrap();
                let (a, z) = match dim.kind {
                    DimensionKind::Width => (
                        Point::new(b.x, b.y + 130.0),
                        Point::new(b.x + b.width, b.y + 130.0),
                    ),
                    DimensionKind::Height => (
                        Point::new(b.x + 130.0, b.y),
                        Point::new(b.x + 130.0, b.y + b.height),
                    ),
                };
                let a = self.screen(a, origin);
                let z = self.screen(z, origin);
                painter.line_segment([a, z], Stroke::new(1.0, Color32::from_gray(140)));
                for p in [a, z] {
                    painter.line_segment(
                        [p - Vec2::splat(3.0), p + Vec2::splat(3.0)],
                        Stroke::new(1.0, Color32::GRAY),
                    );
                }
                painter.text(
                    a + (z - a) * 0.5 + Vec2::new(5.0, -8.0),
                    egui::Align2::CENTER_BOTTOM,
                    self.display(value),
                    egui::FontId::proportional(11.0),
                    Color32::from_gray(95),
                );
            }
        }
        if let Some(p) = response.hover_pos() {
            let world = self.world(p, origin);
            painter.text(
                rect.left_bottom() + Vec2::new(10.0, -10.0),
                egui::Align2::LEFT_BOTTOM,
                format!("X {}   Y {}", self.display(world.x), self.display(world.y)),
                egui::FontId::monospace(12.0),
                Color32::GRAY,
            );
            if let Some(a) = self.first {
                painter.line_segment(
                    [
                        self.screen(a, origin),
                        self.screen(Self::snap(world), origin),
                    ],
                    Stroke::new(3.0, Color32::from_rgb(50, 140, 190)),
                );
            }
            if response.clicked() {
                if let Some(kind) = self.placing.take() {
                    let layer = *d.layers.keys().next().unwrap();
                    let (width, depth) = match kind {
                        FixtureKind::Bath => (inches(60.0), inches(30.0)),
                        FixtureKind::Shower => (inches(36.0), inches(36.0)),
                    };
                    let id = Id::new_v4();
                    self.edit(Command::CreateFixture(Fixture {
                        id,
                        kind,
                        origin: Self::snap(world),
                        width,
                        depth,
                        rotation: 0.0,
                        layer,
                    }));
                    self.selected = Some(id);
                } else if self.drawing {
                    let point = Self::snap(world);
                    if let Some(start) = self.first.take() {
                        let layer = *d.layers.keys().next().unwrap();
                        self.edit(Command::CreateWall(Wall {
                            id: Id::new_v4(),
                            name: "Wall".into(),
                            start,
                            end: point,
                            thickness: 100.0,
                            layer,
                        }));
                    } else {
                        self.first = Some(point);
                    }
                } else {
                    self.selected = self.pick_fixture_or_window(d, world).or_else(|| {
                        d.doors
                            .values()
                            .filter(|v| d.layers[&d.walls[&v.wall].layer].visible)
                            .find(|v| {
                                let w = &d.walls[&v.wall];
                                let l = length(w);
                                let center = Point::new(
                                    w.start.x + (w.end.x - w.start.x) * v.position / l,
                                    w.start.y + (w.end.y - w.start.y) * v.position / l,
                                );
                                (center.x - world.x).hypot(center.y - world.y)
                                    < v.width / 2.0 + 8.0 / self.scale as f64
                                    && distance(w, world)
                                        < w.thickness / 2.0 + 12.0 / self.scale as f64
                            })
                            .map(|v| v.id)
                            .or_else(|| {
                                d.walls
                                    .values()
                                    .filter(|w| d.layers[&w.layer].visible)
                                    .filter_map(|w| {
                                        let dist = distance(w, world);
                                        (dist < w.thickness / 2.0 + 8.0 / self.scale as f64)
                                            .then_some((w.id, dist))
                                    })
                                    .min_by(|a, b| a.1.total_cmp(&b.1))
                                    .map(|v| v.0)
                            })
                    });
                }
            }
            if response.drag_started_by(egui::PointerButton::Primary)
                && !self.drawing
                && let Some(id) = self.selected
                && let Some(w) = d.walls.get(&id)
                && let Some(press) = ui.input(|i| i.pointer.press_origin())
            {
                let start = self.world(press, origin);
                if distance(w, start) < w.thickness / 2.0 + 10.0 / self.scale as f64 {
                    self.drag = Some((id, Self::snap(start)));
                }
            }
        }
        if response.drag_stopped_by(egui::PointerButton::Primary)
            && let Some((id, start)) = self.drag.take()
            && let Some(p) = response.interact_pointer_pos()
        {
            let end = Self::snap(self.world(p, origin));
            let dx = end.x - start.x;
            let dy = end.y - start.y;
            if dx != 0.0 || dy != 0.0 {
                self.edit(Command::MoveWall { id, dx, dy });
            }
        }
    }
}
