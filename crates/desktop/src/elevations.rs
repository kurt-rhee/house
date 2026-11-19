mod cad;
mod svg;

use eframe::egui::{self, Color32, Pos2, Rect, Sense, Stroke, Vec2};
use kurbo::{Line, ParamCurveNearest, Point, Shape};
use std::path::{Path, PathBuf};
use svg::{Drawing, Geometry, Label, Object};

pub struct Elevations {
    pub drawings: Vec<Elevation>,
    zoom: f32,
    pan: Vec2,
    selected: Option<usize>,
    move_right: f64,
    move_up: f64,
}

pub struct Elevation {
    pub id: String,
    pub title: String,
    path: PathBuf,
    mm_per_point: f64,
    source: String,
    drawing: Drawing,
}

impl Elevations {
    pub fn open(project: &Path) -> Result<Option<Self>, String> {
        let Some(name) = project.file_name().and_then(|name| name.to_str()) else {
            return Ok(None);
        };
        let stem = name.strip_suffix(".house.json").unwrap_or(name);
        let directory = project.with_file_name(format!("{stem}.sheets"));
        let index = directory.join("elevations.tsv");
        let manifest = match std::fs::read_to_string(&index) {
            Ok(manifest) => manifest,
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Ok(None),
            Err(error) => return Err(format!("Could not read {}: {error}", index.display())),
        };
        let mut drawings = Vec::new();
        for (line_number, line) in manifest.lines().enumerate() {
            if line.trim().is_empty() {
                continue;
            }
            let mut columns = line.split('\t');
            let id = columns.next().unwrap_or_default();
            let title = columns.next().unwrap_or_default();
            let scale = columns.next().unwrap_or_default().parse::<f64>().ok();
            let mm_per_point = scale
                .map(|value| value / 72.0 * 25.4)
                .filter(|value| value.is_finite() && *value > 0.0);
            let Some(mm_per_point) = mm_per_point.filter(|_| {
                matches!(id.as_bytes(), [b'A' | b'I', b'-', b'0'..=b'9', b'0'..=b'9'])
                    && !title.is_empty()
                    && columns.next().is_none()
                    && !drawings.iter().any(|item: &Elevation| item.id == id)
            }) else {
                return Err(format!(
                    "Invalid elevation entry at {}:{}",
                    index.display(),
                    line_number + 1
                ));
            };
            let path = directory.join(format!("{id}.svg"));
            let source = std::fs::read_to_string(&path)
                .map_err(|error| format!("Could not open {}: {error}", path.display()))?;
            let drawing = Drawing::parse(&source)
                .map_err(|error| format!("Could not open {}: {error}", path.display()))?;
            drawings.push(Elevation {
                id: id.into(),
                title: format!("{id}  {title}"),
                path,
                mm_per_point,
                source,
                drawing,
            });
        }
        Ok((!drawings.is_empty()).then_some(Self {
            drawings,
            zoom: 1.0,
            pan: Vec2::ZERO,
            selected: None,
            move_right: 0.0,
            move_up: 0.0,
        }))
    }

    pub fn reset_camera(&mut self) {
        self.zoom = 1.0;
        self.pan = Vec2::ZERO;
    }

    pub fn switch_view(&mut self) {
        self.reset_camera();
        self.select(None);
    }

    fn select(&mut self, selected: Option<usize>) {
        if self.selected != selected {
            self.selected = selected;
            self.move_right = 0.0;
            self.move_up = 0.0;
        }
    }

    pub fn inspector(&mut self, ui: &mut egui::Ui, index: usize, status: &mut String) {
        ui.heading(&self.drawings[index].title);
        if ui.button("Fit elevation").clicked() {
            self.reset_camera();
        }
        let elevation = &mut self.drawings[index];
        if ui.button("Export elevation DXF").clicked() {
            let path = elevation.path.with_extension("dxf");
            *status = match cad::export(&elevation.drawing, elevation.mm_per_point, &path) {
                Ok(()) => format!("Exported {}", path.display()),
                Err(error) => error,
            };
        }
        ui.separator();
        if let Some(selected) = self.selected {
            let object = &elevation.drawing.objects[selected];
            match &object.geometry {
                Geometry::Path(_) => ui.label("Linework"),
                Geometry::Text(label) => ui.label(&label.text),
            };
            ui.add(
                egui::DragValue::new(&mut self.move_right)
                    .prefix("Right ")
                    .suffix(" mm"),
            );
            ui.add(
                egui::DragValue::new(&mut self.move_up)
                    .prefix("Up ")
                    .suffix(" mm"),
            );
            let moved = self.move_right != 0.0 || self.move_up != 0.0;
            if ui
                .add_enabled(moved, egui::Button::new("Save move"))
                .clicked()
            {
                match elevation.move_object(selected, self.move_right, self.move_up) {
                    Ok(()) => {
                        *status = format!("Saved {}", elevation.path.display());
                        self.move_right = 0.0;
                        self.move_up = 0.0;
                    }
                    Err(error) => *status = error,
                }
            }
        } else {
            ui.label("Click linework or a label to select it.");
        }
        ui.label("Middle or right drag to pan. Scroll to zoom.");
    }

    pub fn show(&mut self, ui: &mut egui::Ui, index: usize) {
        let (response, painter) = ui.allocate_painter(ui.available_size(), Sense::click_and_drag());
        let rect = response.rect;
        painter.rect_filled(rect, 0.0, Color32::from_gray(76));
        let drawing = &self.drawings[index].drawing;
        let size = Vec2::new(
            drawing.bounds.width() as f32,
            drawing.bounds.height() as f32,
        );
        let available = (rect.size() - Vec2::splat(32.0)).max(Vec2::splat(1.0));
        let fit = (available.x / size.x).min(available.y / size.y);
        if response.hovered()
            && let Some(pointer) = ui.input(|input| input.pointer.hover_pos())
        {
            let scroll = ui.input(|input| input.smooth_scroll_delta.y);
            let zoom = (self.zoom * (scroll * 0.002).exp()).clamp(0.25, 12.0);
            let anchor = pointer - rect.center();
            self.pan = anchor + (self.pan - anchor) * (zoom / self.zoom);
            self.zoom = zoom;
        }
        if response.dragged_by(egui::PointerButton::Middle)
            || response.dragged_by(egui::PointerButton::Secondary)
        {
            self.pan += response.drag_delta();
        }
        let scale = fit * self.zoom;
        let paper = Rect::from_center_size(rect.center() + self.pan, size * scale);
        painter.rect_filled(paper, 0.0, Color32::WHITE);
        let painter = painter.with_clip_rect(paper);
        let screen = |point: Point| {
            paper.min
                + Vec2::new(
                    (point.x - drawing.bounds.x0) as f32,
                    (point.y - drawing.bounds.y0) as f32,
                ) * scale
        };
        let click = response
            .clicked()
            .then(|| response.interact_pointer_pos())
            .flatten();
        let drawing_point = click.filter(|point| paper.contains(*point)).map(|click| {
            let offset = (click - paper.min) / scale;
            drawing.bounds.origin() + kurbo::Vec2::new(offset.x.into(), offset.y.into())
        });
        let mut hit = None;
        for (index, item) in drawing.objects.iter().enumerate() {
            let selected = self.selected == Some(index);
            match &item.geometry {
                Geometry::Path(path) => {
                    paint_path(&painter, item, &screen, scale, selected);
                    if let Some(point) = drawing_point {
                        let tolerance = f64::from(4.0 / scale) + item.width / 2.0;
                        if item.fill.is_some() && path.contains(point)
                            || item.stroke.is_some()
                                && item.outline.iter().any(|line| {
                                    line.windows(2).any(|pair| {
                                        Line::new(pair[0], pair[1]).nearest(point, 0.01).distance_sq
                                            <= tolerance * tolerance
                                    })
                                })
                        {
                            hit = Some(index);
                        }
                    }
                }
                Geometry::Text(label) => {
                    if paint_label(
                        &painter,
                        item,
                        label,
                        screen(label.baseline),
                        scale,
                        selected,
                        click.filter(|point| paper.contains(*point)),
                    ) {
                        hit = Some(index);
                    }
                }
            }
        }
        if click.is_some() {
            self.select(hit);
        }
    }
}

impl Elevation {
    fn move_object(&mut self, index: usize, right_mm: f64, up_mm: f64) -> Result<(), String> {
        if !right_mm.is_finite() || !up_mm.is_finite() {
            return Err("Enter finite distances".into());
        }
        let current = std::fs::read_to_string(&self.path).map_err(|error| error.to_string())?;
        if current != self.source {
            return Err("Elevation changed on disk. Reopen the project before editing.".into());
        }
        let object = &self.drawing.objects[index];
        let dx = right_mm / self.mm_per_point;
        let dy = -up_mm / self.mm_per_point;
        let translation = format!("translate({dx} {dy})");
        let attribute = if object.has_transform {
            format!("{translation} ")
        } else {
            format!(" transform=\"{translation}\"")
        };
        let mut source = current;
        source.insert_str(object.transform_start, &attribute);
        let drawing = Drawing::parse(&source)?;
        house_io::atomic_write(&self.path, source.as_bytes())?;
        self.source = source;
        self.drawing = drawing;
        Ok(())
    }
}

fn paint_path(
    painter: &egui::Painter,
    object: &Object,
    screen: &impl Fn(Point) -> Pos2,
    scale: f32,
    selected: bool,
) {
    if let Some(color) = object.fill {
        let mut mesh = egui::Mesh::default();
        mesh.indices.extend(&object.triangles.indices);
        for [x, y] in &object.triangles.vertices {
            mesh.colored_vertex(screen(Point::new((*x).into(), (*y).into())), color);
        }
        if !mesh.indices.is_empty() {
            painter.add(egui::Shape::mesh(mesh));
        }
    }
    if let Some(color) = object.stroke.or(selected.then_some(Color32::GOLD)) {
        let stroke = if selected {
            Stroke::new(2.0, Color32::from_rgb(202, 97, 10))
        } else {
            Stroke::new(object.width as f32 * scale, color)
        };
        for line in &object.outline {
            let points: Vec<_> = line.iter().copied().map(screen).collect();
            if let Some([on, off]) = object.dash {
                painter.extend(egui::Shape::dashed_line(
                    &points,
                    stroke,
                    on * scale,
                    off * scale,
                ));
            } else if points.len() > 1 {
                painter.add(egui::Shape::line(points, stroke));
            }
        }
    }
}

fn paint_label(
    painter: &egui::Painter,
    object: &Object,
    label: &Label,
    baseline: Pos2,
    scale: f32,
    selected: bool,
    click: Option<Pos2>,
) -> bool {
    let Some(color) = object.fill else {
        return false;
    };
    let color = if selected {
        Color32::from_rgb(202, 97, 10)
    } else {
        color
    };
    let galley = painter.layout_no_wrap(
        label.text.clone(),
        egui::FontId::proportional(label.size as f32 * scale * if label.bold { 1.03 } else { 1.0 }),
        color,
    );
    let ascent = galley
        .rows
        .first()
        .and_then(|row| row.glyphs.first().map(|glyph| row.pos.y + glyph.pos.y))
        .unwrap_or(0.0);
    let x = match label.anchor {
        egui::Align::Min => 0.0,
        egui::Align::Center => -galley.size().x / 2.0,
        egui::Align::Max => -galley.size().x,
    };
    let shift = Vec2::new(x, -ascent);
    let rotation = egui::emath::Rot2::from_angle(label.angle as f32);
    let origin = baseline + rotation * shift;
    painter.add(
        egui::epaint::TextShape::new(origin, galley.clone(), color).with_angle(label.angle as f32),
    );
    click.is_some_and(|click| {
        Rect::from_min_size(Pos2::ZERO, galley.size())
            .contains((rotation.inverse() * (click - origin)).to_pos2())
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn moves_vector_geometry_and_exports_at_elevation_scale() {
        let source =
            Path::new(env!("CARGO_MANIFEST_DIR")).join("../../output/floor-plan.house.json");
        let mut elevations = Elevations::open(&source).unwrap().unwrap();
        for (id, expected_height) in [("A-03", 216.0), ("I-02", 144.0)] {
            let elevation = elevations
                .drawings
                .iter_mut()
                .find(|item| item.id == id)
                .unwrap();
            let (index, old_bounds) = elevation
                .drawing
                .objects
                .iter()
                .enumerate()
                .find_map(|(index, object)| {
                    let Geometry::Path(path) = &object.geometry else {
                        return None;
                    };
                    let bounds = path.bounding_box();
                    ((bounds.height() - expected_height).abs() < 0.001 && bounds.width() > 1.0)
                        .then_some((index, bounds))
                })
                .unwrap();
            let temporary =
                std::env::temp_dir().join(format!("house-elevation-{}.svg", uuid::Uuid::new_v4()));
            std::fs::write(&temporary, &elevation.source).unwrap();
            elevation.path = temporary.clone();
            elevation.move_object(index, 304.8, 152.4).unwrap();
            let reopened = Drawing::parse(&std::fs::read_to_string(&temporary).unwrap()).unwrap();
            let Geometry::Path(path) = &reopened.objects[index].geometry else {
                panic!("original geometry retained");
            };
            let moved = path.bounding_box();
            assert!(((moved.x0 - old_bounds.x0) * elevation.mm_per_point - 304.8).abs() < 0.001);
            assert!(((old_bounds.y0 - moved.y0) * elevation.mm_per_point - 152.4).abs() < 0.001);

            let exported = temporary.with_extension("dxf");
            cad::export(&reopened, elevation.mm_per_point, &exported).unwrap();
            let dxf = dxf::Drawing::load_file(&exported).unwrap();
            assert_eq!(
                dxf.header.default_drawing_units,
                dxf::enums::Units::Millimeters
            );
            assert!(dxf.entities().any(|entity| {
                let dxf::entities::EntityType::LwPolyline(line) = &entity.specific else {
                    return false;
                };
                let min_y = line
                    .vertices
                    .iter()
                    .map(|p| p.y)
                    .fold(f64::INFINITY, f64::min);
                let max_y = line
                    .vertices
                    .iter()
                    .map(|p| p.y)
                    .fold(f64::NEG_INFINITY, f64::max);
                let min_x = line
                    .vertices
                    .iter()
                    .map(|p| p.x)
                    .fold(f64::INFINITY, f64::min);
                (max_y - min_y - 2438.4).abs() < 0.02
                    && (min_x - moved.x0 * elevation.mm_per_point).abs() < 0.02
            }));
            assert!(dxf.entities().any(|entity| matches!(&entity.specific, dxf::entities::EntityType::Text(text) if text.value == "8′–0″" || text.value.contains("WALL HEIGHT"))));
            std::fs::remove_file(temporary).unwrap();
            std::fs::remove_file(exported).unwrap();
        }
    }
}
