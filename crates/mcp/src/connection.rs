//! Protected, per-launch connection discovery for local native agents.
use super::LocalServer;
use serde_json::json;
use std::{io::Write, path::Path};

impl LocalServer {
    pub fn publish_connection(&mut self, path: impl AsRef<Path>) -> Result<(), String> {
        let path = path.as_ref();
        let parent = path
            .parent()
            .ok_or("Connection file needs a parent directory")?;
        let mut directory = std::fs::DirBuilder::new();
        directory.recursive(true);
        #[cfg(unix)]
        {
            use std::os::unix::fs::DirBuilderExt;
            directory.mode(0o700);
        }
        directory.create(parent).map_err(|e| e.to_string())?;
        let temporary = parent.join(format!(".mcp-{}.tmp", house_core::Id::new_v4()));
        let result = (|| {
            let mut options = std::fs::OpenOptions::new();
            options.write(true).create_new(true);
            #[cfg(unix)]
            {
                use std::os::unix::fs::OpenOptionsExt;
                options.mode(0o600);
            }
            let mut file = options.open(&temporary)?;
            let data = json!({"url":format!("http://{}/mcp",self.address),"token":self.token});
            file.write_all(data.to_string().as_bytes())?;
            file.sync_all()?;
            std::fs::rename(&temporary, path)
        })();
        if let Err(error) = result {
            let _ = std::fs::remove_file(temporary);
            return Err(error.to_string());
        }
        self.connection_file = Some(path.into());
        Ok(())
    }

    pub(super) fn remove_connection_file(&mut self) {
        if let Some(path) = self.connection_file.take() {
            // A replacement server may already own the discovery file.
            let owned = std::fs::read(&path)
                .ok()
                .and_then(|bytes| serde_json::from_slice::<serde_json::Value>(&bytes).ok())
                .is_some_and(|data| data["token"] == self.token);
            if owned {
                let _ = std::fs::remove_file(path);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use crate::{DocumentHandle, start_local};
    #[test]
    fn connection_file_is_private_rotates_and_preserves_new_owner() {
        let directory =
            std::env::temp_dir().join(format!("house-connection-{}", house_core::Id::new_v4()));
        let path = directory.join("mcp.json");
        let handle = DocumentHandle::spawn(house_core::bathroom(), || {}).unwrap();
        let mut first = start_local(handle.clone(), 0).unwrap();
        first.publish_connection(&path).unwrap();
        let data: serde_json::Value =
            serde_json::from_slice(&std::fs::read(&path).unwrap()).unwrap();
        assert_eq!(data["token"], first.token);
        assert_eq!(data["url"], format!("http://{}/mcp", first.address));
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            assert_eq!(
                std::fs::metadata(&path).unwrap().permissions().mode() & 0o777,
                0o600
            );
            assert_eq!(
                std::fs::metadata(&directory).unwrap().permissions().mode() & 0o777,
                0o700
            );
        }
        let mut replacement = start_local(handle, 0).unwrap();
        replacement.publish_connection(&path).unwrap();
        assert_ne!(first.token, replacement.token);
        drop(first);
        assert!(path.exists());
        drop(replacement);
        assert!(!path.exists());
        std::fs::remove_dir(directory).unwrap();
    }
}
