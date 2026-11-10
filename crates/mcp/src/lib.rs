//! Shared document actor and loopback MCP transport.
use house_commands::Command;
use house_core::*;
use rmcp::{
    ServerHandler,
    handler::server::{router::tool::ToolRouter, wrapper::Parameters},
    model::{CallToolResult, ContentBlock, ServerCapabilities, ServerConfig},
    tool, tool_handler, tool_router,
};
use schemars::JsonSchema;
use serde::Deserialize;
use serde_json::json;
use std::sync::Arc;
use tokio::sync::oneshot;
mod connection;
mod document;
pub use document::{Action, DocumentHandle, Pending, PendingError, Reply};
#[derive(Clone)]
pub struct CadServer {
    handle: DocumentHandle,
    tool_router: ToolRouter<Self>,
}
#[derive(Deserialize, JsonSchema)]
pub struct WallInput {
    /// Optional revision returned by get_document. A stale revision rejects the edit without changes.
    pub expected_revision: Option<u64>,
    pub name: String,
    pub x1: f64,
    pub y1: f64,
    pub x2: f64,
    pub y2: f64,
    pub thickness: f64,
}
#[derive(Deserialize, JsonSchema)]
pub struct WallUpdate {
    pub id: String,
    #[serde(flatten)]
    pub wall: WallInput,
}
#[derive(Deserialize, JsonSchema)]
pub struct MoveInput {
    /// Optional revision returned by get_document. A stale revision rejects the edit without changes.
    pub expected_revision: Option<u64>,
    pub id: String,
    /// Translation in millimeters; six inches is 152.4.
    pub dx: f64,
    pub dy: f64,
}
#[derive(Deserialize, JsonSchema)]
pub struct DoorInput {
    /// Optional revision returned by get_document. A stale revision rejects the edit without changes.
    pub expected_revision: Option<u64>,
    pub wall_id: String,
    pub position: f64,
    pub width: f64,
    /// "left" or "right".
    pub swing: String,
}
#[derive(Deserialize, JsonSchema)]
pub struct DoorUpdate {
    /// True places the hinge at the opening end; omit to preserve the current hinge.
    pub hinge_at_end: Option<bool>,
    /// Omit to preserve the existing type; "hinged", "sliding_glass", "french_glass", "garage", or "pocket".
    pub kind: Option<String>,
    /// Optional revision returned by get_document. A stale revision rejects the edit without changes.
    pub expected_revision: Option<u64>,
    pub id: String,
    pub wall_id: String,
    pub position: f64,
    pub width: f64,
    pub swing: String,
}
#[derive(Deserialize, JsonSchema)]
pub struct OpeningInput {
    pub expected_revision: Option<u64>,
    pub wall_id: String,
    /// Center distance along the host wall, in millimeters.
    pub position: f64,
    pub width: f64,
}
#[derive(Deserialize, JsonSchema)]
pub struct WindowUpdate {
    pub id: String,
    #[serde(flatten)]
    pub opening: OpeningInput,
}
#[derive(Deserialize, JsonSchema)]
pub struct FixtureInput {
    pub expected_revision: Option<u64>,
    /// Origin (local top-left before clockwise rotation), in millimeters.
    pub x: f64,
    pub y: f64,
    pub width: f64,
    pub depth: f64,
    /// Clockwise degrees about the origin; defaults to zero.
    #[serde(default)]
    pub rotation: f64,
}
#[derive(Deserialize, JsonSchema)]
pub struct FixtureUpdate {
    pub id: String,
    #[serde(flatten)]
    pub geometry: FixtureInput,
}
#[derive(Deserialize, JsonSchema)]
pub struct FixtureFinishInput {
    pub id: String,
    pub expected_revision: Option<u64>,
    /// Finish description; omit to preserve, empty string clears it.
    pub material: Option<String>,
    /// Fixture style; omit to preserve, empty string clears it.
    pub style: Option<String>,
}
#[derive(Deserialize, JsonSchema)]
pub struct IdInput {
    /// Optional revision returned by get_document. A stale revision rejects the edit without changes.
    pub expected_revision: Option<u64>,
    pub id: String,
}
#[derive(Deserialize, JsonSchema)]
pub struct RoomLabelInput {
    pub expected_revision: Option<u64>,
    pub name: String,
    pub x: f64,
    pub y: f64,
}
#[derive(Deserialize, JsonSchema)]
pub struct RoomInput {
    pub expected_revision: Option<u64>,
    /// Name displayed at the center of the room on the drawing and exports.
    pub name: String,
    /// Stable IDs of the four enclosing axis-aligned walls, from get_document.
    pub west: String,
    pub east: String,
    pub north: String,
    pub south: String,
}
#[derive(Deserialize, JsonSchema)]
pub struct RenameRoomInput {
    pub expected_revision: Option<u64>,
    /// Stable room ID from get_document.
    pub id: String,
    pub name: String,
}
#[derive(Deserialize, JsonSchema)]
pub struct PathInput {
    /// Absolute or working-directory-relative local path.
    pub path: String,
}
fn parse_id(s: &str) -> Result<Id, String> {
    Id::parse_str(s).map_err(|e| e.to_string())
}
fn swing(s: &str) -> Result<Swing, String> {
    match s.to_lowercase().as_str() {
        "left" => Ok(Swing::Left),
        "right" => Ok(Swing::Right),
        _ => Err("Swing must be left or right".into()),
    }
}
fn result(r: Reply) -> CallToolResult {
    match r {
        Ok(v) => CallToolResult::success(vec![ContentBlock::text(v.to_string())]),
        Err(e) => CallToolResult::error(vec![ContentBlock::text(e)]),
    }
}
impl CadServer {
    async fn edit(&self, command: Command, expected_revision: Option<u64>) -> Reply {
        let action = match expected_revision {
            Some(expected_revision) => Action::EditAtRevision {
                command,
                expected_revision,
            },
            None => Action::Edit(command),
        };
        self.handle.request(action).await
    }
    async fn create_fixture(&self, p: FixtureInput, kind: FixtureKind) -> Reply {
        let id = Id::new_v4();
        let layer = *self.handle.snapshot().layers.keys().next().unwrap();
        self.edit(
            Command::CreateFixture(Fixture {
                material: None,
                style: None,
                id,
                kind,
                origin: Point::new(p.x, p.y),
                width: p.width,
                depth: p.depth,
                rotation: p.rotation,
                layer,
            }),
            p.expected_revision,
        )
        .await
        .map(|mut v| {
            v["id"] = json!(id);
            v
        })
    }
    pub fn new(handle: DocumentHandle) -> Self {
        Self {
            handle,
            tool_router: Self::tool_router(),
        }
    }
}
#[tool_router]
impl CadServer {
    #[tool(
        description = "Read the full semantic document, including IDs and revision. All coordinates are millimeters."
    )]
    async fn get_document(&self) -> CallToolResult {
        result(self.handle.request(Action::Read).await)
    }
    #[tool(
        description = "List semantic objects and their stable IDs. Find Partition by its wall name before moving it."
    )]
    async fn list_objects(&self) -> CallToolResult {
        result(self.handle.request(Action::Read).await)
    }
    #[tool(description = "Create a semantic wall. Coordinates and thickness are millimeters.")]
    async fn create_wall(&self, Parameters(p): Parameters<WallInput>) -> CallToolResult {
        let id = Id::new_v4();
        let layer = *self.handle.snapshot().layers.keys().next().unwrap();
        let r = self
            .edit(
                Command::CreateWall(Wall {
                    id,
                    name: p.name,
                    start: Point::new(p.x1, p.y1),
                    end: Point::new(p.x2, p.y2),
                    thickness: p.thickness,
                    layer,
                }),
                p.expected_revision,
            )
            .await
            .map(|mut v| {
                v["id"] = json!(id);
                v
            });
        result(r)
    }
    #[tool(description = "Update wall endpoints, name and thickness, preserving ID and layer. Attached opening stations scale with wall length; reposition openings afterward when preserving world positions. Millimeters.")]
    async fn update_wall(&self, Parameters(p): Parameters<WallUpdate>) -> CallToolResult {
        let r = match parse_id(&p.id).ok().and_then(|id| self.handle.snapshot().walls.get(&id).cloned()) {
            Some(mut w) => {
                w.name = p.wall.name;
                w.start = Point::new(p.wall.x1, p.wall.y1);
                w.end = Point::new(p.wall.x2, p.wall.y2);
                w.thickness = p.wall.thickness;
                self.edit(Command::UpdateWall(w), p.wall.expected_revision).await
            }
            None => Err("Wall not found".into()),
        };
        result(r)
    }
    #[tool(
        description = "Translate an identified wall by dx/dy millimeters. Attached openings follow. Move Partition six inches right using dx=152.4,dy=0."
    )]
    async fn move_wall(&self, Parameters(p): Parameters<MoveInput>) -> CallToolResult {
        let r = match parse_id(&p.id) {
            Ok(id) => {
                self.edit(
                    Command::MoveWall {
                        id,
                        dx: p.dx,
                        dy: p.dy,
                    },
                    p.expected_revision,
                )
                .await
            }
            Err(e) => Err(e),
        };
        result(r)
    }
    #[tool(
        description = "Create a door on a host wall. Position is opening center distance from wall start in millimeters."
    )]
    async fn create_door(&self, Parameters(p): Parameters<DoorInput>) -> CallToolResult {
        let r = match (parse_id(&p.wall_id), swing(&p.swing)) {
            (Ok(wall), Ok(swing)) => {
                let id = Id::new_v4();
                self.edit(
                    Command::CreateDoor(Door {
                        hinge_at_end: false,
                        id,
                        wall,
                        position: p.position,
                        width: p.width,
                        kind: house_core::DoorKind::Hinged,
                        swing,
                    }),
                    p.expected_revision,
                )
                .await
                .map(|mut v| {
                    v["id"] = json!(id);
                    v
                })
            }
            _ => Err("Invalid host ID or swing".into()),
        };
        result(r)
    }
    #[tool(
        description = "Replace door properties, retaining its stable ID. Invalid edits are rejected atomically."
    )]
    async fn update_door(&self, Parameters(p): Parameters<DoorUpdate>) -> CallToolResult {
        let kind = match p.kind.as_deref() {
            Some("hinged") => DoorKind::Hinged,
            Some("sliding_glass") => DoorKind::SlidingGlass,
            Some("french_glass") => DoorKind::FrenchGlass,
            Some("garage") => DoorKind::Garage,
            Some("pocket") => DoorKind::Pocket,
            None => match parse_id(&p.id)
                .ok()
                .and_then(|id| self.handle.snapshot().doors.get(&id).map(|v| v.kind))
            {
                Some(kind) => kind,
                None => return result(Err("Door not found".into())),
            },
            _ => {
                return result(Err(
                    "Door kind must be hinged, sliding_glass, french_glass, garage, or pocket"
                        .into(),
                ));
            }
        };
        let r = match (parse_id(&p.id), parse_id(&p.wall_id), swing(&p.swing)) {
            (Ok(id), Ok(wall), Ok(swing)) => {
                self.edit(
                    Command::UpdateDoor(Door {
                        hinge_at_end: p.hinge_at_end.unwrap_or_else(|| {
                            self.handle
                                .snapshot()
                                .doors
                                .get(&id)
                                .is_some_and(|d| d.hinge_at_end)
                        }),
                        id,
                        wall,
                        position: p.position,
                        width: p.width,
                        kind,
                        swing,
                    }),
                    p.expected_revision,
                )
                .await
            }
            _ => Err("Invalid ID or swing".into()),
        };
        result(r)
    }
    #[tool(
        description = "Create a wall-hosted window. Position and width are millimeters; overlapping openings are rejected."
    )]
    async fn create_window(&self, Parameters(p): Parameters<OpeningInput>) -> CallToolResult {
        let id = Id::new_v4();
        let r = match parse_id(&p.wall_id) {
            Ok(wall) => {
                self.edit(
                    Command::CreateWindow(Window {
                        id,
                        wall,
                        position: p.position,
                        width: p.width,
                    }),
                    p.expected_revision,
                )
                .await
            }
            Err(e) => Err(e),
        };
        result(r.map(|mut v| {
            v["id"] = json!(id);
            v
        }))
    }
    #[tool(
        description = "Update a window's host, center station and width atomically; millimeters."
    )]
    async fn update_window(&self, Parameters(p): Parameters<WindowUpdate>) -> CallToolResult {
        let r = match (parse_id(&p.id), parse_id(&p.opening.wall_id)) {
            (Ok(id), Ok(wall)) => {
                self.edit(
                    Command::UpdateWindow(Window {
                        id,
                        wall,
                        position: p.opening.position,
                        width: p.opening.width,
                    }),
                    p.opening.expected_revision,
                )
                .await
            }
            _ => Err("Invalid window or host ID".into()),
        };
        result(r)
    }
    #[tool(
        description = "Create a sliding glass door on a host wall. Position is center station; width is total opening width, in millimeters. No swing arc."
    )]
    async fn create_sliding_glass_door(
        &self,
        Parameters(p): Parameters<OpeningInput>,
    ) -> CallToolResult {
        let id = Id::new_v4();
        let r = match parse_id(&p.wall_id) {
            Ok(wall) => {
                self.edit(
                    Command::CreateDoor(Door {
                        hinge_at_end: false,
                        id,
                        wall,
                        position: p.position,
                        width: p.width,
                        swing: Swing::Left,
                        kind: DoorKind::SlidingGlass,
                    }),
                    p.expected_revision,
                )
                .await
            }
            Err(e) => Err(e),
        };
        result(r.map(|mut v| {
            v["id"] = json!(id);
            v
        }))
    }
    #[tool(
        description = "Place a bath footprint. x/y, width and depth are millimeters; rotation is clockwise degrees. Freestanding, with no automatic wall attachment."
    )]
    async fn create_bath(&self, Parameters(p): Parameters<FixtureInput>) -> CallToolResult {
        result(self.create_fixture(p, FixtureKind::Bath).await)
    }
    #[tool(
        description = "Place a shower footprint. x/y, width and depth are millimeters; rotation is clockwise degrees. Freestanding, with no automatic wall attachment."
    )]
    async fn create_shower(&self, Parameters(p): Parameters<FixtureInput>) -> CallToolResult {
        result(self.create_fixture(p, FixtureKind::Shower).await)
    }
    #[tool(
        description = "Place a toilet footprint. Local top is the tank against the wall; depth extends forward. Millimeters, clockwise rotation."
    )]
    async fn create_toilet(&self, Parameters(p): Parameters<FixtureInput>) -> CallToolResult {
        result(self.create_fixture(p, FixtureKind::Toilet).await)
    }
    #[tool(
        description = "Place a sink vanity footprint. Local top is the back against the wall. Millimeters, clockwise rotation."
    )]
    async fn create_sink(&self, Parameters(p): Parameters<FixtureInput>) -> CallToolResult {
        result(self.create_fixture(p, FixtureKind::Sink).await)
    }
    #[tool(
        description = "Place a countertop footprint. Millimeters and clockwise rotation; local top is the back against the wall."
    )]
    async fn create_countertop(&self, Parameters(p): Parameters<FixtureInput>) -> CallToolResult {
        result(self.create_fixture(p, FixtureKind::Countertop).await)
    }
    #[tool(
        description = "Place a four-burner stove footprint. Millimeters and clockwise rotation; local top is the back against the wall."
    )]
    async fn create_stove(&self, Parameters(p): Parameters<FixtureInput>) -> CallToolResult {
        result(self.create_fixture(p, FixtureKind::Stove).await)
    }
    #[tool(
        description = "Place a refrigerator footprint. Local top is the back; doors face local bottom. Millimeters and clockwise rotation."
    )]
    async fn create_refrigerator(&self, Parameters(p): Parameters<FixtureInput>) -> CallToolResult {
        result(self.create_fixture(p, FixtureKind::Refrigerator).await)
    }
    #[tool(
        description = "Place a countertop appliance garage cabinet with a roll-up front. Local top is the back; front faces local bottom. Millimeters and clockwise rotation."
    )]
    async fn create_appliance_garage(
        &self,
        Parameters(p): Parameters<FixtureInput>,
    ) -> CallToolResult {
        result(self.create_fixture(p, FixtureKind::ApplianceGarage).await)
    }

    #[tool(
        description = "Place a single dishwasher drawer footprint. Local top is the back; drawer opens toward local bottom. Millimeters and clockwise rotation."
    )]
    async fn create_dishwasher_drawer(
        &self,
        Parameters(p): Parameters<FixtureInput>,
    ) -> CallToolResult {
        result(self.create_fixture(p, FixtureKind::DishwasherDrawer).await)
    }
    #[tool(
        description = "Place an all-in-one front-loading washer-dryer footprint. Local top is the back. Millimeters and clockwise rotation."
    )]
    async fn create_washer_dryer(&self, Parameters(p): Parameters<FixtureInput>) -> CallToolResult {
        result(self.create_fixture(p, FixtureKind::WasherDryer).await)
    }
    #[tool(
        description = "Place a cabinet containing separate pull-out trash and recycling bins. Local top is the back. Millimeters and clockwise rotation."
    )]
    async fn create_waste_cabinet(
        &self,
        Parameters(p): Parameters<FixtureInput>,
    ) -> CallToolResult {
        result(self.create_fixture(p, FixtureKind::WasteCabinet).await)
    }

    #[tool(
        description = "Place a bed footprint with headboard at local top. Millimeters and clockwise rotation. Standard king is 1930.4 wide by 2032 deep."
    )]
    async fn create_bed(&self, Parameters(p): Parameters<FixtureInput>) -> CallToolResult {
        result(self.create_fixture(p, FixtureKind::Bed).await)
    }

    #[tool(
        description = "Place an overhead hanging wardrobe footprint with a schematic pull-down rail. Dashed plan outline; mounting height and mechanism travel require separate elevation verification. Local top is the back. Millimeters and clockwise rotation."
    )]
    async fn create_overhead_wardrobe(
        &self,
        Parameters(p): Parameters<FixtureInput>,
    ) -> CallToolResult {
        result(self.create_fixture(p, FixtureKind::OverheadWardrobe).await)
    }

    #[tool(description = "Place a floor-standing wardrobe with bypass fronts and fixed hanging rail. Local top is the back. Millimeters and clockwise rotation.")]
    async fn create_wardrobe(&self, Parameters(p): Parameters<FixtureInput>) -> CallToolResult {
        result(self.create_fixture(p, FixtureKind::Wardrobe).await)
    }
    #[tool(description = "Place quarter-round open shelves, attached at the local left edge with back at local top. Equal width and depth give a quarter circle. Millimeters and clockwise rotation.")]
    async fn create_quarter_round_shelves(&self, Parameters(p): Parameters<FixtureInput>) -> CallToolResult {
        result(self.create_fixture(p, FixtureKind::QuarterRoundShelves).await)
    }

    #[tool(
        description = "Assign material and style to an existing fixture, preserving geometry and ID. Saved in the house document and included in SVG/DXF export metadata. Omitted fields are preserved; empty strings clear them."
    )]
    async fn set_fixture_finish(
        &self,
        Parameters(p): Parameters<FixtureFinishInput>,
    ) -> CallToolResult {
        let r = match parse_id(&p.id)
            .ok()
            .and_then(|id| self.handle.snapshot().fixtures.get(&id).cloned())
        {
            Some(mut f) => {
                if let Some(v) = p.material {
                    f.material = if v.trim().is_empty() { None } else { Some(v) };
                }
                if let Some(v) = p.style {
                    f.style = if v.trim().is_empty() { None } else { Some(v) };
                }
                self.edit(Command::UpdateFixture(f), p.expected_revision)
                    .await
            }
            None => Err("Fixture not found".into()),
        };
        result(r)
    }

    #[tool(
        description = "Move, resize or rotate an existing fixture, preserving its type and ID. Millimeters and clockwise degrees."
    )]
    async fn update_fixture(&self, Parameters(p): Parameters<FixtureUpdate>) -> CallToolResult {
        let r = match parse_id(&p.id)
            .ok()
            .and_then(|id| self.handle.snapshot().fixtures.get(&id).cloned())
        {
            Some(mut f) => {
                f.origin = Point::new(p.geometry.x, p.geometry.y);
                f.width = p.geometry.width;
                f.depth = p.geometry.depth;
                f.rotation = p.geometry.rotation;
                self.edit(Command::UpdateFixture(f), p.geometry.expected_revision)
                    .await
            }
            None => Err("Fixture not found".into()),
        };
        result(r)
    }
    #[tool(
        description = "Create a named rectangular room bounded by the inside faces of four existing axis-aligned walls. Use wall IDs from get_document for west/east/north/south. The name appears at the room center on the live drawing and SVG/DXF exports; it follows boundary wall moves. Invalid boundaries are rejected atomically."
    )]
    async fn create_room(&self, Parameters(p): Parameters<RoomInput>) -> CallToolResult {
        let r = async {
            let id = Id::new_v4();
            self.edit(
                Command::CreateRoom(Room {
                    id,
                    name: p.name,
                    west: parse_id(&p.west)?,
                    east: parse_id(&p.east)?,
                    north: parse_id(&p.north)?,
                    south: parse_id(&p.south)?,
                }),
                p.expected_revision,
            )
            .await
            .map(|mut v| {
                v["id"] = json!(id);
                v
            })
        }
        .await;
        result(r)
    }
    #[tool(
        description = "Place a room name at x/y millimeters for open or irregular spaces, without adding walls or claiming measured area. Rename with rename_room; delete with delete_object."
    )]
    async fn create_room_label(&self, Parameters(p): Parameters<RoomLabelInput>) -> CallToolResult {
        let id = Id::new_v4();
        result(
            self.edit(
                Command::CreateRoomLabel(RoomLabel {
                    id,
                    name: p.name,
                    position: Point::new(p.x, p.y),
                }),
                p.expected_revision,
            )
            .await
            .map(|mut value| {
                value["id"] = json!(id);
                value
            }),
        )
    }
    #[tool(
        description = "Rename an existing room using its ID from get_document. Updates the label on the live drawing and SVG/DXF exports, preserving boundaries and dimensions. Undoable."
    )]
    async fn rename_room(&self, Parameters(p): Parameters<RenameRoomInput>) -> CallToolResult {
        let r = match parse_id(&p.id) {
            Ok(id) => {
                self.edit(
                    Command::RenameRoom { id, name: p.name },
                    p.expected_revision,
                )
                .await
            }
            Err(e) => Err(e),
        };
        result(r)
    }
    #[tool(
        description = "Delete an unreferenced object. Referenced walls are protected by relationship validation."
    )]
    async fn delete_object(&self, Parameters(p): Parameters<IdInput>) -> CallToolResult {
        let r = match parse_id(&p.id) {
            Ok(id) => {
                self.edit(Command::DeleteObject { id }, p.expected_revision)
                    .await
            }
            Err(e) => Err(e),
        };
        result(r)
    }
    #[tool(description = "Undo the last committed edit, including GUI edits.")]
    async fn undo(&self) -> CallToolResult {
        result(self.handle.request(Action::Undo).await)
    }
    #[tool(description = "Redo the last undone edit.")]
    async fn redo(&self) -> CallToolResult {
        result(self.handle.request(Action::Redo).await)
    }
    #[tool(description = "Save the shared document as versioned JSON to a local path.")]
    async fn save_project(&self, Parameters(p): Parameters<PathInput>) -> CallToolResult {
        result(self.handle.request(Action::Save(p.path.into())).await)
    }
    #[tool(description = "Export the current shared drawing to a local SVG file.")]
    async fn export_svg(&self, Parameters(p): Parameters<PathInput>) -> CallToolResult {
        result(self.handle.request(Action::Export(p.path.into())).await)
    }
    #[tool(
        description = "Export the current shared drawing as a millimeter DXF file. Dimensions become lines and text; JSON remains the editable project format."
    )]
    async fn export_dxf(&self, Parameters(p): Parameters<PathInput>) -> CallToolResult {
        result(self.handle.request(Action::ExportDxf(p.path.into())).await)
    }
}
#[tool_handler(router = self.tool_router)]
impl ServerHandler for CadServer {
    fn get_info(&self) -> ServerConfig {
        ServerConfig::new(ServerCapabilities::builder().enable_tools().build()).with_instructions("House architectural drafting. Millimeters; x right, y down. Find semantic IDs with get_document. Changes affect the live desktop. Preliminary design only.")
    }
}
/// Token is generated locally per app launch; it is not a cloud account credential.
pub struct LocalServer {
    pub address: std::net::SocketAddr,
    pub token: String,
    stop: Option<oneshot::Sender<()>>,
    enabled: Arc<std::sync::atomic::AtomicBool>,
    connection_file: Option<std::path::PathBuf>,
}
impl Drop for LocalServer {
    fn drop(&mut self) {
        self.enabled
            .store(false, std::sync::atomic::Ordering::Release);
        self.remove_connection_file();
        if let Some(s) = self.stop.take() {
            let _ = s.send(());
        }
    }
}
pub fn start_local(handle: DocumentHandle, port: u16) -> Result<LocalServer, String> {
    let listener = std::net::TcpListener::bind(("127.0.0.1", port)).map_err(|e| e.to_string())?;
    let address = listener.local_addr().map_err(|e| e.to_string())?;
    listener.set_nonblocking(true).map_err(|e| e.to_string())?;
    let token = Id::new_v4().to_string();
    let expected = format!("Bearer {token}");
    let (stop, rx) = oneshot::channel();
    let runtime = tokio::runtime::Runtime::new().map_err(|e| e.to_string())?;
    let enabled = Arc::new(std::sync::atomic::AtomicBool::new(true));
    let check_enabled = enabled.clone();
    // Shutdown happens on this background thread; dropping LocalServer never joins on the UI.
    std::thread::spawn(move || {
        runtime.block_on(async move {
            use rmcp::transport::streamable_http_server::{
                StreamableHttpServerConfig, StreamableHttpService,
                session::local::LocalSessionManager,
            };
            let config = StreamableHttpServerConfig::default()
                .with_allowed_hosts([format!("127.0.0.1:{}", address.port())])
                .enforce_origin_validation();
            let cancellation = config.cancellation_token.clone();
            let service = StreamableHttpService::new(
                move || Ok(CadServer::new(handle.clone())),
                Arc::new(LocalSessionManager::default()),
                config,
            );
            let auth = axum::middleware::from_fn(
                move |req: axum::extract::Request, next: axum::middleware::Next| {
                    let expected = expected.clone();
                    let enabled = check_enabled.clone();
                    async move {
                        if !enabled.load(std::sync::atomic::Ordering::Acquire)
                            || req
                                .headers()
                                .get("authorization")
                                .and_then(|h| h.to_str().ok())
                                != Some(expected.as_str())
                        {
                            return axum::response::Response::builder()
                                .status(401)
                                .body(axum::body::Body::empty())
                                .unwrap();
                        }
                        next.run(req).await
                    }
                },
            );
            let app = axum::Router::new()
                .nest_service("/mcp", service)
                .layer(auth);
            let listener = tokio::net::TcpListener::from_std(listener).unwrap();
            tokio::select! {
                _=async {let _=axum::serve(listener,app).await;}=>{},
                _=rx=>{cancellation.cancel();}
            }
            // Dropping the runtime also cancels idle/half-open HTTP connections.
        })
    });
    Ok(LocalServer {
        address,
        token,
        stop: Some(stop),
        enabled,
        connection_file: None,
    })
}
