//! CAD interchange snapshot, in millimeters with positive Y pointing north.
use super::atomic_write;
use dxf::XData;
use dxf::XDataItem;
use dxf::{
    Color, Drawing, LwPolylineVertex, Point as CadPoint,
    entities::{Arc, Entity, EntityType, Line, LwPolyline, Text},
    enums::{
        AcadVersion, DrawingUnits, HorizontalTextJustification, Units, VerticalTextJustification,
    },
    tables::{AppId, Layer as CadLayer},
};
use house_core::{DimensionKind, Document, Id, Layer, Point, Swing, Wall};
use house_geometry::{dimension_value, length, room_bounds, validate, wall_polygon};
use std::path::Path;
mod compatibility;

/// Export drawing entities rather than a second editable architectural model.
pub fn dxf_bytes(document: &Document) -> Result<Vec<u8>, String> {
    validate(document)?;
    let mut output = Export::new();
    for layer in document.layers.values().filter(|layer| layer.visible) {
        for (kind, color) in [("WALLS", 7), ("DOORS", 4), ("WINDOWS", 5)] {
            output.layer(&layer_name(kind, layer), color);
        }
    }
    output.layer("ROOMS", 3);
    output.layer("DIMENSIONS", 8);
    for wall in document
        .walls
        .values()
        .filter(|w| document.layers[&w.layer].visible)
    {
        let layer = layer_name("WALLS", &document.layers[&wall.layer]);
        // Split at opening intervals so CAD consumers see genuine gaps, not white overlays.
        let mut openings: Vec<(f64, f64)> = document
            .doors
            .values()
            .filter(|v| v.wall == wall.id)
            .map(|v| (v.position - v.width / 2.0, v.position + v.width / 2.0))
            .chain(
                document
                    .windows
                    .values()
                    .filter(|v| v.wall == wall.id)
                    .map(|v| (v.position - v.width / 2.0, v.position + v.width / 2.0)),
            )
            .collect();
        openings.sort_by(|a, b| a.0.total_cmp(&b.0));
        let mut station = 0.0;
        for (start, end) in openings {
            output.wall_span(wall, station, start, &layer);
            station = end;
        }
        output.wall_span(wall, station, length(wall), &layer);
    }
    for door in document.doors.values() {
        let host = &document.walls[&door.wall];
        if !document.layers[&host.layer].visible {
            continue;
        }
        let layer = layer_name("DOORS", &document.layers[&host.layer]);
        let hinge = on_wall(host, door.position - door.width / 2.0);
        let l = length(host);
        let (ux, uy) = (
            (host.end.x - host.start.x) / l,
            (host.end.y - host.start.y) / l,
        );
        let sign = if door.swing == Swing::Left { 1.0 } else { -1.0 };
        let open = Point::new(
            hinge.x - uy * door.width * sign,
            hinge.y + ux * door.width * sign,
        );
        output.line(hinge, open, &layer, door.id);
        // DXF arcs run counterclockwise. Reflecting Y reverses the model's swing direction.
        let base = (-uy).atan2(ux).to_degrees();
        let (start, end) = if door.swing == Swing::Left {
            (base - 90.0, base)
        } else {
            (base, base + 90.0)
        };
        output.arc(
            hinge,
            door.width,
            start.rem_euclid(360.0),
            end.rem_euclid(360.0),
            &layer,
            door.id,
        );
    }
    for window in document.windows.values() {
        let host = &document.walls[&window.wall];
        if !document.layers[&host.layer].visible {
            continue;
        }
        let layer = layer_name("WINDOWS", &document.layers[&host.layer]);
        output.line(
            on_wall(host, window.position - window.width / 2.0),
            on_wall(host, window.position + window.width / 2.0),
            &layer,
            window.id,
        );
    }
    for room in document.rooms.values() {
        let b = room_bounds(document, room)?;
        let center = Point::new(b.x + b.width / 2.0, b.y + b.height / 2.0);
        output.text(&room.name, center, 65.0, "ROOMS", room.id);
        output.text(
            &format!("{:.2} m²", b.area() / 1e6),
            Point::new(center.x, center.y + 90.0),
            55.0,
            "ROOMS",
            room.id,
        );
    }
    for dimension in document.dimensions.values() {
        let b = room_bounds(document, &document.rooms[&dimension.room])?;
        let value = dimension_value(document, dimension)?;
        let (a, z) = match dimension.kind {
            DimensionKind::Width => (
                Point::new(b.x, b.y + 120.0),
                Point::new(b.x + b.width, b.y + 120.0),
            ),
            DimensionKind::Height => (
                Point::new(b.x + 120.0, b.y),
                Point::new(b.x + 120.0, b.y + b.height),
            ),
        };
        output.line(a, z, "DIMENSIONS", dimension.id);
        for p in [a, z] {
            output.line(
                Point::new(p.x - 20.0, p.y - 20.0),
                Point::new(p.x + 20.0, p.y + 20.0),
                "DIMENSIONS",
                dimension.id,
            );
        }
        let label = Point::new((a.x + z.x) / 2.0 + 20.0, (a.y + z.y) / 2.0 - 50.0);
        output.text(
            &format!("{value:.1} mm"),
            label,
            45.0,
            "DIMENSIONS",
            dimension.id,
        );
    }
    output.drawing.header.minimum_drawing_extents = output.min;
    output.drawing.header.maximum_drawing_extents = output.max;
    let mut bytes = Vec::new();
    output.drawing.save(&mut bytes).map_err(|e| e.to_string())?;
    compatibility::table_handles(bytes, output.drawing.header.next_available_handle)
}
pub fn export_dxf(document: &Document, path: &Path) -> Result<(), String> {
    atomic_write(path, &dxf_bytes(document)?)
}
fn cad(p: Point) -> CadPoint {
    CadPoint::new(p.x, -p.y, 0.0)
}
fn on_wall(w: &Wall, station: f64) -> Point {
    let t = station / length(w);
    Point::new(
        w.start.x + (w.end.x - w.start.x) * t,
        w.start.y + (w.end.y - w.start.y) * t,
    )
}
fn layer_name(kind: &str, source: &Layer) -> String {
    let name: String = source
        .name
        .chars()
        .take(48)
        .map(|c| {
            if c.is_alphanumeric() || c == '-' || c == '_' {
                c
            } else {
                '_'
            }
        })
        .collect();
    format!("{kind}_{name}_{}", source.id.simple())
}
struct Export {
    drawing: Drawing,
    min: CadPoint,
    max: CadPoint,
}
impl Export {
    fn new() -> Self {
        let mut drawing = Drawing::new();
        drawing.header.version = AcadVersion::R2007;
        drawing.header.default_drawing_units = Units::Millimeters;
        drawing.header.drawing_units = DrawingUnits::Metric;
        drawing.add_app_id(AppId {
            name: "HOUSE".into(),
            ..Default::default()
        });
        Self {
            drawing,
            min: CadPoint::origin(),
            max: CadPoint::origin(),
        }
    }
    fn layer(&mut self, name: &str, color: u8) {
        self.drawing.add_layer(CadLayer {
            name: name.into(),
            color: Color::from_index(color),
            ..Default::default()
        });
    }
    fn track(&mut self, p: Point) {
        let p = cad(p);
        self.min.x = self.min.x.min(p.x);
        self.min.y = self.min.y.min(p.y);
        self.max.x = self.max.x.max(p.x);
        self.max.y = self.max.y.max(p.y);
    }
    fn add(&mut self, kind: EntityType, layer: &str, id: Id) {
        let mut entity = Entity::new(kind);
        entity.common.layer = layer.into();
        // dxf 0.6.2 defaults to invalid group 440 value 0. Use explicit opaque alpha.
        entity.common.transparency = 0x0200_00ff;
        entity.common.x_data.push(XData {
            application_name: "HOUSE".into(),
            items: vec![XDataItem::Str(id.to_string())],
        });
        self.drawing.add_entity(entity);
    }
    fn wall_span(&mut self, wall: &Wall, start: f64, end: f64, layer: &str) {
        if end <= start {
            return;
        }
        let segment = Wall {
            start: on_wall(wall, start),
            end: on_wall(wall, end),
            ..wall.clone()
        };
        let points = wall_polygon(&segment);
        for p in points {
            self.track(p);
        }
        let mut poly = LwPolyline {
            vertices: points
                .iter()
                .map(|p| LwPolylineVertex {
                    x: p.x,
                    y: -p.y,
                    ..Default::default()
                })
                .collect(),
            ..Default::default()
        };
        poly.set_is_closed(true);
        self.add(EntityType::LwPolyline(poly), layer, wall.id);
    }
    fn line(&mut self, a: Point, b: Point, layer: &str, id: Id) {
        self.track(a);
        self.track(b);
        self.add(EntityType::Line(Line::new(cad(a), cad(b))), layer, id);
    }
    fn arc(&mut self, center: Point, radius: f64, start: f64, end: f64, layer: &str, id: Id) {
        // A conservative circle bound also contains the quarter-circle swing.
        self.track(Point::new(center.x - radius, center.y - radius));
        self.track(Point::new(center.x + radius, center.y + radius));
        self.add(
            EntityType::Arc(Arc::new(cad(center), radius, start, end)),
            layer,
            id,
        );
    }
    fn text(&mut self, value: &str, point: Point, height: f64, layer: &str, id: Id) {
        self.track(point);
        // TEXT is single-line: prevent label newlines from becoming DXF group-code lines.
        let value = value
            .chars()
            .map(|c| if c.is_control() { ' ' } else { c })
            .collect();
        let text = Text {
            value,
            location: cad(point),
            second_alignment_point: cad(point),
            text_height: height,
            horizontal_text_justification: HorizontalTextJustification::Center,
            vertical_text_justification: VerticalTextJustification::Middle,
            ..Default::default()
        };
        self.add(EntityType::Text(text), layer, id);
    }
}

#[cfg(test)]
mod tests;
