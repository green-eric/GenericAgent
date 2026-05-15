use std::process::{Command, Child};
use std::sync::Mutex;
use std::net::TcpStream;
use std::time::{Duration, Instant};
use std::thread;
use std::path::PathBuf;

#[cfg(windows)]
use std::os::windows::process::CommandExt;

static BRIDGE_PROCESS: Mutex<Option<Child>> = Mutex::new(None);

fn find_bridge_script() -> PathBuf {
    // exe is at frontends/GenericAgent.exe
    // bridge is at frontends/desktop_bridge.py
    let exe_dir = std::env::current_exe()
        .expect("cannot get exe path")
        .parent()
        .expect("cannot get exe dir")
        .to_path_buf();
    exe_dir.join("desktop_bridge.py")
}

fn wait_for_port(port: u16, timeout: Duration) -> bool {
    let start = Instant::now();
    while start.elapsed() < timeout {
        if TcpStream::connect(("127.0.0.1", port)).is_ok() {
            return true;
        }
        thread::sleep(Duration::from_millis(100));
    }
    false
}

fn start_bridge() {
    let script = find_bridge_script();
    if !script.exists() {
        eprintln!("[tauri] bridge script not found: {:?}", script);
        return;
    }

    let show_console = std::env::args().any(|a| a == "--console");

    let mut cmd = Command::new("python");
    cmd.arg(&script)
       .current_dir(script.parent().unwrap());

    #[cfg(windows)]
    if !show_console {
        const CREATE_NO_WINDOW: u32 = 0x08000000;
        cmd.creation_flags(CREATE_NO_WINDOW);
    }

    let child = cmd.spawn().expect("failed to start desktop_bridge.py");

    eprintln!("[tauri] started bridge PID={}", child.id());
    *BRIDGE_PROCESS.lock().unwrap() = Some(child);

    if !wait_for_port(14168, Duration::from_secs(15)) {
        eprintln!("[tauri] WARNING: bridge did not become ready within 15s");
    }
}

fn stop_bridge() {
    if let Some(mut child) = BRIDGE_PROCESS.lock().unwrap().take() {
        eprintln!("[tauri] stopping bridge PID={}", child.id());
        let _ = child.kill();
        let _ = child.wait();
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    start_bridge();

    tauri::Builder::default()
        .on_window_event(|_window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                stop_bridge();
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");

    stop_bridge();
}
