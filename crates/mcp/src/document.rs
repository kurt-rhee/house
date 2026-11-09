//! One mutable document engine for native and network clients.
use house_commands::{Command, Engine};
use house_core::Document;
use serde_json::{Value, json};
use std::{
    path::PathBuf,
    sync::{Arc, RwLock, mpsc},
};
use tokio::sync::oneshot;

pub enum Action {
    Edit(Command),
    EditAtRevision {
        command: Command,
        expected_revision: u64,
    },
    Undo,
    Redo,
    Open(PathBuf),
    Save(PathBuf),
    Export(PathBuf),
    ExportDxf(PathBuf),
    Read,
}
pub type Reply = Result<Value, String>;
pub use tokio::sync::oneshot::error::TryRecvError as PendingError;
pub type Pending = oneshot::Receiver<Reply>;
struct Request {
    action: Action,
    reply: oneshot::Sender<Reply>,
}
#[derive(Clone)]
pub struct DocumentHandle {
    sender: mpsc::SyncSender<Request>,
    snapshot: Arc<RwLock<Arc<Document>>>,
}
impl DocumentHandle {
    pub fn spawn(
        document: Document,
        repaint: impl Fn() + Send + Sync + 'static,
    ) -> Result<Self, String> {
        let mut engine = Engine::new(document)?;
        let snapshot = Arc::new(RwLock::new(Arc::new(engine.document().clone())));
        let published = snapshot.clone();
        let (sender, receiver) = mpsc::sync_channel::<Request>(256);
        std::thread::Builder::new()
            .name("house-document".into())
            .spawn(move || {
                for request in receiver {
                    let revision = engine.document().revision;
                    let result = process(&mut engine, request.action);
                    // Read/save/export and rejected edits keep the published Arc intact.
                    if engine.document().revision != revision {
                        *published.write().unwrap() = Arc::new(engine.document().clone());
                    }
                    let _ = request.reply.send(result);
                    repaint();
                }
            })
            .map_err(|e| e.to_string())?;
        Ok(Self { sender, snapshot })
    }
    pub fn snapshot(&self) -> Arc<Document> {
        self.snapshot.read().unwrap().clone()
    }
    pub fn submit(&self, action: Action) -> Result<Pending, String> {
        let (reply, rx) = oneshot::channel();
        self.sender
            .try_send(Request { action, reply })
            .map_err(|e| e.to_string())?;
        Ok(rx)
    }
    pub async fn request(&self, action: Action) -> Reply {
        self.submit(action)?.await.map_err(|e| e.to_string())?
    }
}
fn process(engine: &mut Engine, action: Action) -> Reply {
    match action {
        Action::Edit(command) => engine.execute(command).map(|r| json!({"revision":r})),
        Action::EditAtRevision {
            command,
            expected_revision,
        } => engine
            .execute_at_revision(command, expected_revision)
            .map(|r| json!({"revision":r})),
        Action::Undo => engine.undo().map(|r| json!({"revision":r})),
        Action::Redo => engine.redo().map(|r| json!({"revision":r})),
        Action::Read => describe(engine.document()),
        Action::Open(path) => house_io::load(&path)
            .and_then(|d| engine.replace(d))
            .map(|_| json!({"revision":engine.document().revision})),
        Action::Save(path) => house_io::save(engine.document(), &path)
            .map(|_| json!({"saved":path,"revision":engine.document().revision})),
        Action::Export(path) => house_io::export_svg(engine.document(), &path)
            .map(|_| json!({"exported":path,"revision":engine.document().revision})),
        Action::ExportDxf(path) => house_io::export_dxf(engine.document(), &path)
            .map(|_| json!({"exported":path,"revision":engine.document().revision})),
    }
}
fn describe(d: &Document) -> Reply {
    let mut value = serde_json::to_value(d).map_err(|e| e.to_string())?;
    let rooms = d
        .rooms
        .values()
        .map(|room| {
            let bounds = house_geometry::room_bounds(d, room)?;
            let measurement = json!({
                "id": room.id,
                "name": room.name,
                "width_mm": bounds.width,
                "height_mm": bounds.height,
                "area_mm2": bounds.area()
            });
            Ok(measurement)
        })
        .collect::<Result<Vec<Value>, String>>()?;
    let dimensions = d
        .dimensions
        .values()
        .map(|dim| {
            let value = house_geometry::dimension_value(d, dim)?;
            Ok(json!({"id":dim.id,"value_mm":value}))
        })
        .collect::<Result<Vec<Value>, String>>()?;
    value["room_measurements"] = json!(rooms);
    value["dimension_measurements"] = json!(dimensions);
    Ok(value)
}
