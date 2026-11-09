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
    /// Optional revision returned by get_document. A stale revision rejects the edit without changes.
    pub expected_revision: Option<u64>,
    pub id: String,
    pub wall_id: String,
    pub position: f64,
    pub width: f64,
    pub swing: String,
}
#[derive(Deserialize, JsonSchema)]
pub struct IdInput {
    /// Optional revision returned by get_document. A stale revision rejects the edit without changes.
    pub expected_revision: Option<u64>,
    pub id: String,
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
                        id,
                        wall,
                        position: p.position,
                        width: p.width,
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
        let r = match (parse_id(&p.id), parse_id(&p.wall_id), swing(&p.swing)) {
            (Ok(id), Ok(wall), Ok(swing)) => {
                self.edit(
                    Command::UpdateDoor(Door {
                        id,
                        wall,
                        position: p.position,
                        width: p.width,
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
}
impl Drop for LocalServer {
    fn drop(&mut self) {
        self.enabled
            .store(false, std::sync::atomic::Ordering::Release);
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
    })
}
