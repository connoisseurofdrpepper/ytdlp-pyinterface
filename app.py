import json
import os
import platform
import queue as pyqueue
import re
import shlex
import shutil
import subprocess
import sys
import threading
import time
import zipfile
import io
import base64
from pathlib import Path
from tkinter import BOTH, LEFT, RIGHT, TOP, BOTTOM, X, Y, NSEW, END, DISABLED, NORMAL, StringVar, IntVar, BooleanVar, HORIZONTAL, TclError
from tkinter import filedialog
from urllib.parse import urlparse
import ttkbootstrap as tb
from ttkbootstrap.dialogs import Messagebox
from ttkbootstrap.scrolled import ScrolledFrame, ScrolledText
import webbrowser
import warnings
import copy
from datetime import datetime, timedelta

from runner import Runner, Task
from presets import list_presets, preset_args

try:
    from PIL import Image, ImageTk, __version__ as pil_ver
except ImportError:
    Image = None
    ImageTk = None
    pil_ver = None

warnings.filterwarnings("ignore", message="urllib3 .* or chardet .* doesn't match a supported version")

try:
    import requests
except ImportError:
    requests = None

APP_NAME = "ytdlp-pyinterface"
APP_VERSION = "1.0.1"
REPO_RELEASES_URL = "https://github.com/connoisseurofdrpepper/ytdlp-interface/releases"
USER_PROFILE_URL = "https://github.com/connoisseurofdrpepper"
ORIGINAL_REPO_URL = "https://github.com/ErrorFlynn/ytdlp-interface"
GHOSTY_REPO_URL = "https://github.com/TheFrenchGhosty/TheFrenchGhostys-Ultimate-YouTube-DL-Scripts-Collection"

# Base64 encoded 16x16 YouTube favicon
YOUTUBE_FAVICON_B64 = "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAl0lEQVQ4jWNkoBAwUqifYdQABgYGBkYVAz9//mRkZGRkYGBgYGBg+P//PwMDAwMDw48fP/5//vxlsbKy/g+2z8DAwMAA5YQBw/8/s/9//s/A8O/v/z8DAwMDwz8/f/5/9v/f//8ZGBgYGBgYGBh+//37/+/79+/+v3z58v/v37//Z2BgYGBgYGBg+Pfv3/9/f//+//v37//v37//Z2BgYAAA7B8Uqf4lA80AAAAASUVORK5CYII="

class Config(dict):
    def __init__(self, path: Path):
        super().__init__()
        self.path = path
        self.update(self._defaults())
        
        if self.path.exists():
            self._load_from_file()
        else:
            self.save()

    def _defaults(self):
        return {
            "show_format_col": True,
            "show_format_note_col": True,
            "show_ext_col": True,
            "show_filesize_col": True,
            "show_website_favicon_col": False,
            "show_website_text_col": False,
            "finish_action": "none",
            "ui_theme": "system",
            "ui_snap_windows": True,
            "ui_no_min_width": False,
            "ui_exact_filesize": False,
            "ui_browse_start_path": "current",
            "sb_enable": False,
            "sb_mark": [],
            "sb_remove": [],
            "queue_max_concurrent": 1,
            "queue_max_data_instances": 4,
            "queue_start_on_lengthy": True,
            "queue_autostart_on_stop": False,
            "queue_item_has_own_options": True,
            "queue_autostart_on_launch": False,
            "queue_save_error_items": False,
            "queue_remove_done_items": False,
            "queue_paste_on_activate": False,
            "queue_retry": 2,
            "queue_retry_sleep": 5,
            "upd_check_on_start": False,
            "upd_only_extract_exe": True,
            "upd_ytdlp_channel": "stable",
            "upd_extract_ffplay": False,
            "keep_video": True,
            "embed_metadata": True,
            "embed_thumbnail": False,
            "embed_subtitles": False,
            "convert_to_mp3": False,
            "chapter_mode": "ignore",
            "force_keyframes": False,
            "rate_limit_value": "",
            "rate_limit_unit": "MB/s",
            "output_template": "%(title)s [%(id)s].%(ext)s",
            "custom_args": "",
            "download_folder": str(Path.home() / "Downloads"),
            "file_mod_write_time": True,
            "ffmpeg_path": "",
            "ytdlp_path": "",
            "preferred_resolution": "none",
            "prefer_higher_framerate": False,
            "preferred_video_container": "none",
            "preferred_audio_container": "none",
            "preferred_video_codec": "none",
            "preferred_audio_codec": "none",
            "youtube_android_client": False,
            "playlist_indexing": "%(playlist_index)d - ",
            "pad_playlist_index": False,
            "playlist_in_folder": False,
            "use_proxy": False,
            "proxy_url": "",
            "cookies_from_browser": "none",
            "cookie_file_path": "",
            "console_keyword_highlighting": True,
            "console_limited_buffer": True,
        }

    def _load_from_file(self):
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                self.update(data)
        except (json.JSONDecodeError, IOError) as e:
            print(f"CONFIG LOAD ERROR: {e}")
            Messagebox.show_error(
                f"Could not load settings from:\n{self.path}\n\n"
                f"The file might be corrupted. Defaults will be used.\n\n"
                f"Error details: {e}",
                title="Configuration Load Error"
            )

    def save(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"--- CONFIGURATION SAVE FAILED ---\nPath: {self.path}\nError: {e}\n---------------------------------")
            try:
                Messagebox.show_error(
                    f"Could not save settings to:\n{self.path}\n\n"
                    f"Please ensure you have write permissions for this folder.\n\n"
                    f"Error details: {e}",
                    title="Configuration Save Error"
                )
            except Exception as mb_e:
                print(f"Messagebox failed to show: {mb_e}")

def is_windows(): return platform.system().lower() == "windows"
def is_macos(): return platform.system().lower() == "darwin"
def is_linux(): return platform.system().lower() == "linux"

def perform_finish_action(action: str):
    try:
        if action == "shutdown":
            if is_windows():
                subprocess.Popen(["shutdown", "/s", "/t", "0"])
            elif is_macos():
                subprocess.Popen(["osascript", "-e", 'tell application "System Events" to shut down'])
            elif is_linux():
                if shutil.which("systemctl"):
                    subprocess.Popen(["systemctl", "poweroff"])
                else:
                    subprocess.Popen(["shutdown", "now"])
        elif action == "hibernate":
            if is_windows():
                subprocess.Popen(["shutdown", "/h"])
            elif is_linux():
                subprocess.Popen(["systemctl", "hibernate"])
            else:
                print("Hibernate not supported on this OS.")
        elif action == "sleep":
            if is_windows():
                subprocess.Popen(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
            elif is_macos():
                subprocess.Popen(["osascript", "-e", 'tell application "System Events" to sleep'])
            elif is_linux():
                subprocess.Popen(["systemctl", "suspend"])
        elif action == "exit":
            pass
    except Exception as e:
        Messagebox.show_error(f"Failed to perform '{action}': {e}", title="When finished")

def build_sponsorblock_flags(cfg: Config):
    flags = []
    if cfg.get("sb_enable", False):
        if cfg.get("sb_mark"):
            flags += ["--sponsorblock-mark", ",".join(cfg["sb_mark"])]
        if cfg.get("sb_remove"):
            flags += ["--sponsorblock-remove", ",".join(cfg["sb_remove"])]
    return flags

def build_yt_dlp_cmd(cfg: Config, url: str, preset_args: list = None):
    ytdlp_exe = "yt-dlp"
    if cfg.get("ytdlp_path") and Path(cfg["ytdlp_path"]).exists():
        ytdlp_exe = cfg["ytdlp_path"]
    
    cmd = [ytdlp_exe, url]

    if preset_args:
        cmd.extend(preset_args)
    else:
        # This block is for regular (non-preset) downloads
        is_audio_only = cfg.get("convert_to_mp3", False)
        if is_audio_only:
            cmd += ["-x", "--audio-format", "mp3"]
        else:
            res = cfg.get("preferred_resolution", "none")
            v_container = cfg.get("preferred_video_container", "none")
            a_container = cfg.get("preferred_audio_container", "none")
            v_codec = cfg.get("preferred_video_codec", "none")
            a_codec = cfg.get("preferred_audio_codec", "none")
            
            fmt = "bv"
            if v_codec != "none": fmt += f"[vcodec~={v_codec}]"
            if v_container != "none": fmt += f"[ext={v_container}]"
            fmt += "+ba"
            if a_codec != "none": fmt += f"[acodec~={a_codec}]"
            if a_container != "none": fmt += f"[ext={a_container}]"
            if res != "none": fmt += f"[height<={res[:-1]}]"

            if cfg.get("prefer_higher_framerate", False):
                fmt += "/b[fps>30]"

            cmd += ["-f", fmt]

            if not cfg.get("keep_video", True):
                cmd += ["--remux-video", "mp4"]

    # This part applies to both regular and preset downloads
    outdir = cfg.get("download_folder", str(Path.home() / "Downloads"))
    template = cfg.get("output_template", "%(title)s [%(id)s].%(ext)s")

    # For presets, remove existing output path to replace it with the global one
    if preset_args:
        try:
            out_index = cmd.index("-o") if "-o" in cmd else cmd.index("--output")
            cmd.pop(out_index) # remove -o
            cmd.pop(out_index) # remove path
        except ValueError:
            pass # No -o flag in preset, which is fine
    
    cmd += ["-o", str(Path(outdir) / template)]

    if is_windows():
        cmd.append("--windows-filenames")

    rate_value = cfg.get("rate_limit_value", "").strip()
    if rate_value:
        rate_unit = cfg.get("rate_limit_unit", "MB/s")
        suffix = {'KB/s': 'K', 'MB/s': 'M'}.get(rate_unit, '')
        cmd += ["--limit-rate", f"{rate_value}{suffix}"]

    if cfg.get("embed_metadata", True): cmd += ["--embed-metadata"]
    if cfg.get("embed_thumbnail", True): cmd += ["--embed-thumbnail"]
    if cfg.get("embed_subtitles", False): cmd += ["--embed-subs"]
    
    if cfg.get("file_mod_write_time", True):
        cmd += ["--no-mtime"]
    else:
        cmd += ["--write-last-modified-time"]

    chapter_mode = cfg.get("chapter_mode", "ignore")
    if chapter_mode == "split": cmd += ["--split-chapters"]
    elif chapter_mode == "embedded": cmd += ["--embed-chapters"]
    
    if cfg.get("force_keyframes", False): cmd += ["--force-keyframes-at-cuts"]
    
    if cfg.get("youtube_android_client", False): cmd += ["--youtube-client", "android"]
    
    if cfg.get("use_proxy", False) and cfg.get("proxy_url", "").strip(): cmd += ["--proxy", cfg.get("proxy_url").strip()]

    browser = cfg.get("cookies_from_browser", "none")
    cookie_file = cfg.get("cookie_file_path", "")
    if cookie_file and Path(cookie_file).exists():
        cmd += ["--cookies", cookie_file]
    elif browser != "none":
        cmd += ["--cookies-from-browser", browser]

    cmd += build_sponsorblock_flags(cfg)
    
    ffmpeg_path = cfg.get("ffmpeg_path", "").strip()
    if ffmpeg_path and Path(ffmpeg_path).exists():
        cmd += ["--ffmpeg-location", ffmpeg_path]
    
    extra = cfg.get("custom_args", "").strip()
    if extra and not preset_args: # only add custom args for non-preset downloads
        try: cmd += shlex.split(extra)
        except Exception: cmd += extra.split()
        
    return cmd

class FFmpegUpdater:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.progress_callback = None
        
    def set_progress_callback(self, callback):
        self.progress_callback = callback
        
    def _progress(self, message):
        if self.progress_callback:
            self.progress_callback(message)
    
    def get_ffmpeg_version(self, ffmpeg_path=None):
        exe_path = "ffmpeg"
        if ffmpeg_path:
            exe_path = str(Path(ffmpeg_path) / "ffmpeg")
        
        try:
            proc = subprocess.run([exe_path, "-version"], capture_output=True, text=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW if is_windows() else 0)
            if proc.returncode == 0:
                first_line = proc.stdout.split('\n')[0]
                if 'version' in first_line:
                    parts = first_line.split()
                    for i, part in enumerate(parts):
                        if part == 'version' and i + 1 < len(parts):
                            return parts[i + 1].strip('-gpl').strip('-git')
                return first_line
        except Exception:
            pass
        return None
    
    def get_latest_ffmpeg_version(self):
        if not requests:
            self._progress("Error: requests module not available")
            return None
            
        try:
            self._progress("Checking for latest ffmpeg version...")
            resp = requests.get("https://api.github.com/repos/BtbN/FFmpeg-Builds/releases/latest", timeout=15)
            if resp.status_code == 200:
                tag = resp.json()["tag_name"]
                return tag.replace("autobuild-", "")
        except Exception as e:
            self._progress(f"Error checking latest version: {e}")
        return None
    
    def download_ffmpeg(self):
        if not requests:
            self._progress("Error: requests module not available for download")
            return False
            
        try:
            if is_windows():
                return self._download_ffmpeg_windows()
            elif is_macos():
                return self._download_ffmpeg_macos()
            elif is_linux():
                return self._download_ffmpeg_linux()
            else:
                self._progress("Unsupported operating system")
                return False
        except Exception as e:
            self._progress(f"Error downloading ffmpeg: {e}")
            return False
    
    def _download_ffmpeg_windows(self):
        self._progress("Downloading ffmpeg for Windows...")
        app_dir = Path.home() / ".ytdlp-interface"
        app_dir.mkdir(exist_ok=True)
        
        try:
            url = "https://github.com/BtbN/FFmpeg-Builds/releases/latest/download/ffmpeg-master-latest-win64-gpl.zip"
            zip_path = app_dir / "ffmpeg.zip"
            
            self._progress("Downloading ffmpeg archive...")
            with requests.get(url, stream=True, timeout=30) as r:
                r.raise_for_status()
                with open(zip_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk: f.write(chunk)
            
            self._progress("Extracting ffmpeg...")
            ffmpeg_dir = app_dir / "ffmpeg"
            if ffmpeg_dir.exists(): shutil.rmtree(ffmpeg_dir)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                for member in zip_ref.namelist():
                    if member.endswith("ffmpeg.exe") or (self.cfg.get("upd_extract_ffplay") and member.endswith("ffplay.exe")):
                        zip_ref.extract(member, app_dir)
                        extracted_file = app_dir / member
                        target_dir = ffmpeg_dir / "bin"
                        target_dir.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(extracted_file), str(target_dir / extracted_file.name))

            for item in app_dir.iterdir():
                if item.is_dir() and item.name.startswith("ffmpeg-"):
                    shutil.rmtree(item)

            zip_path.unlink()
            
            ffmpeg_bin_dir = app_dir / "ffmpeg" / "bin"
            if (ffmpeg_bin_dir / "ffmpeg.exe").exists():
                self.cfg["ffmpeg_path"] = str(ffmpeg_bin_dir)
                self.cfg.save()
                self._progress("ffmpeg installed successfully!")
                return True
            else:
                self._progress("Error: ffmpeg.exe not found in extracted files")
                return False
                
        except Exception as e:
            self._progress(f"Error installing ffmpeg: {e}")
            return False
    
    def _download_ffmpeg_macos(self):
        self._progress("Downloading ffmpeg for macOS...")
        app_dir = Path.home() / ".ytdlp-interface"
        app_dir.mkdir(exist_ok=True)
        ffmpeg_dir = app_dir / "ffmpeg"
        
        try:
            url = f"https://evermeet.cx/ffmpeg/getrelease/zip"
            zip_path = app_dir / "ffmpeg.zip"
            
            self._progress("Downloading ffmpeg archive...")
            with requests.get(url, stream=True, timeout=30) as r:
                r.raise_for_status()
                with open(zip_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192): f.write(chunk)
            
            self._progress("Extracting ffmpeg...")
            ffmpeg_dir.mkdir(exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                for member in zip_ref.namelist():
                    if member == "ffmpeg" or (self.cfg.get("upd_extract_ffplay") and member == "ffplay"):
                        zip_ref.extract(member, ffmpeg_dir)

            zip_path.unlink()
            
            ffmpeg_exe = ffmpeg_dir / "ffmpeg"
            if ffmpeg_exe.exists():
                os.chmod(ffmpeg_exe, 0o755)
                if (ffmpeg_dir / "ffplay").exists(): os.chmod(ffmpeg_dir / "ffplay", 0o755)
                self.cfg["ffmpeg_path"] = str(ffmpeg_dir)
                self.cfg.save()
                self._progress("ffmpeg installed successfully!")
                return True
            else:
                self._progress("Error: ffmpeg binary not found")
                return False
                
        except Exception as e:
            self._progress(f"Error installing ffmpeg: {e}")
            return False
    
    def _download_ffmpeg_linux(self):
        return super()._download_ffmpeg_linux()

    def check_and_update_ffmpeg(self):
        custom_path = self.cfg.get("ffmpeg_path", "").strip()
        current_version = self.get_ffmpeg_version(custom_path if custom_path else None)
        
        if not current_version:
            self._progress("ffmpeg not found. Installing...")
            return self.download_ffmpeg()
        
        latest_version = self.get_latest_ffmpeg_version()
        
        if not latest_version:
            self._progress(f"Current ffmpeg version: {current_version}")
            self._progress("Could not check for updates")
            return True
        
        self._progress(f"Current: {current_version}, Latest: {latest_version}")
        
        if current_version not in latest_version:
            self._progress("New version available. Updating...")
            return self.download_ffmpeg()
        else:
            self._progress("ffmpeg is up to date!")
            return True

class SettingsWindow(tb.Toplevel):
    def __init__(self, master, cfg: Config, theme_apply_cb=None):
        super().__init__(master)
        self.title(f"{APP_NAME} Settings")
        self.geometry("800x600")
        self.minsize(750, 550)
        self.cfg = cfg
        self.theme_apply_cb = theme_apply_cb
        self.ffmpeg_updater = FFmpegUpdater(cfg)
        self.master_window = master
        self.bind("<Escape>", lambda e: self.destroy())
        
        nb = tb.Notebook(self)
        nb.pack(fill=BOTH, expand=True, padx=10, pady=10)

        ytdlp_tab_container = tb.Frame(nb)
        nb.add(ytdlp_tab_container, text="yt-dlp")
        f_ytdlp = ScrolledFrame(ytdlp_tab_container, autohide=True)
        f_ytdlp.pack(fill=BOTH, expand=True)
        self._build_ytdlp(f_ytdlp)

        f_sb = tb.Frame(nb)
        nb.add(f_sb, text="SponsorBlock")
        self._build_sponsorblock(f_sb)

        f_q = tb.Frame(nb)
        nb.add(f_q, text="Queueing")
        self._build_queueing(f_q)

        f_ui = tb.Frame(nb)
        nb.add(f_ui, text="Interface")
        self._build_interface(f_ui)

        f_upd = tb.Frame(nb)
        nb.add(f_upd, text="Updater")
        self._build_updater(f_upd)

        f_about = tb.Frame(nb)
        nb.add(f_about, text="About")
        self._build_about(f_about)

    def _build_ytdlp(self, frame):
        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(3, weight=1)
        
        tb.Label(frame, text="Preferred resolution:").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        res_opts = ["none", "4320p", "2160p", "1440p", "1080p", "720p", "480p", "360p", "240p", "144p"]
        var_res = StringVar(value=self.cfg.get("preferred_resolution", "none"))
        dd_res = tb.Combobox(frame, textvariable=var_res, values=res_opts, state="readonly", width=10)
        dd_res.grid(row=0, column=1, sticky="w", padx=8, pady=6)
        dd_res.bind("<<ComboboxSelected>>", lambda e: self._save("preferred_resolution", var_res.get()))

        v_fps = BooleanVar(value=self.cfg.get("prefer_higher_framerate", False))
        tb.Checkbutton(frame, text="Prefer a higher framerate", variable=v_fps, command=lambda: self._save("prefer_higher_framerate", v_fps.get())) \
            .grid(row=0, column=2, columnspan=2, sticky="w", padx=8, pady=6)

        tb.Label(frame, text="Preferred video container:").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        container_opts = ["none", "mp4", "webm", "mkv", "mov", "avi", "flv"]
        var_v_cont = StringVar(value=self.cfg.get("preferred_video_container", "none"))
        dd_v_cont = tb.Combobox(frame, textvariable=var_v_cont, values=container_opts, state="readonly", width=10)
        dd_v_cont.grid(row=1, column=1, sticky="w", padx=8, pady=6)
        dd_v_cont.bind("<<ComboboxSelected>>", lambda e: self._save("preferred_video_container", var_v_cont.get()))

        tb.Label(frame, text="Preferred audio container:").grid(row=1, column=2, sticky="e", padx=8, pady=6)
        audio_container_opts = ["none", "m4a", "webm", "mp3", "opus", "flac", "wav"]
        var_a_cont = StringVar(value=self.cfg.get("preferred_audio_container", "none"))
        dd_a_cont = tb.Combobox(frame, textvariable=var_a_cont, values=audio_container_opts, state="readonly", width=10)
        dd_a_cont.grid(row=1, column=3, sticky="w", padx=8, pady=6)
        dd_a_cont.bind("<<ComboboxSelected>>", lambda e: self._save("preferred_audio_container", var_a_cont.get()))
        
        tb.Label(frame, text="Preferred video codec:").grid(row=2, column=0, sticky="w", padx=8, pady=6)
        vcodec_opts = ["none", "av01", "vp9", "h264"]
        var_v_codec = StringVar(value=self.cfg.get("preferred_video_codec", "none"))
        dd_v_codec = tb.Combobox(frame, textvariable=var_v_codec, values=vcodec_opts, state="readonly", width=10)
        dd_v_codec.grid(row=2, column=1, sticky="w", padx=8, pady=6)
        dd_v_codec.bind("<<ComboboxSelected>>", lambda e: self._save("preferred_video_codec", var_v_codec.get()))

        tb.Label(frame, text="Preferred audio codec:").grid(row=2, column=2, sticky="e", padx=8, pady=6)
        acodec_opts = ["none", "opus", "aac", "vorbis"]
        var_a_codec = StringVar(value=self.cfg.get("preferred_audio_codec", "none"))
        dd_a_codec = tb.Combobox(frame, textvariable=var_a_codec, values=acodec_opts, state="readonly", width=10)
        dd_a_codec.grid(row=2, column=3, sticky="w", padx=8, pady=6)
        dd_a_codec.bind("<<ComboboxSelected>>", lambda e: self._save("preferred_audio_codec", var_a_codec.get()))
        
        v_android = BooleanVar(value=self.cfg.get("youtube_android_client", False))
        tb.Checkbutton(frame, text="[YouTube] Use the Android player client for video extraction", variable=v_android, command=lambda: self._save("youtube_android_client", v_android.get())) \
            .grid(row=3, column=0, columnspan=4, sticky="w", padx=8, pady=6)
        
        tb.Separator(frame).grid(row=4, column=0, columnspan=4, sticky="ew", padx=8, pady=10)
        
        row = 5
        tb.Label(frame, text="Output template:").grid(row=row, column=0, sticky="w", padx=8, pady=6)
        var_tpl = StringVar(value=self.cfg.get("output_template"))
        ent_tpl = tb.Entry(frame, textvariable=var_tpl)
        ent_tpl.grid(row=row, column=1, columnspan=2, sticky="ew", padx=8, pady=6)
        ent_tpl.bind("<FocusOut>", lambda e: self._save("output_template", var_tpl.get()))
        btn_reset_tpl = tb.Button(frame, text="Reset to default", command=lambda: var_tpl.set(self.cfg._defaults()["output_template"]))
        btn_reset_tpl.grid(row=row, column=3, padx=8)

        row += 1
        tb.Label(frame, text="Playlist indexing:").grid(row=row, column=0, sticky="w", padx=8, pady=6)
        var_playlist_tpl = StringVar(value=self.cfg.get("playlist_indexing"))
        ent_playlist_tpl = tb.Entry(frame, textvariable=var_playlist_tpl)
        ent_playlist_tpl.grid(row=row, column=1, columnspan=2, sticky="ew", padx=8, pady=6)
        ent_playlist_tpl.bind("<FocusOut>", lambda e: self._save("playlist_indexing", var_playlist_tpl.get()))
        btn_reset_playlist_tpl = tb.Button(frame, text="Reset to default", command=lambda: var_playlist_tpl.set(self.cfg._defaults()["playlist_indexing"]))
        btn_reset_playlist_tpl.grid(row=row, column=3, padx=8)

        row += 1
        v_pad = BooleanVar(value=self.cfg.get("pad_playlist_index", False))
        tb.Checkbutton(frame, text="Pad the indexed filenames with zeroes", variable=v_pad, command=lambda: self._save("pad_playlist_index", v_pad.get())) \
            .grid(row=row, column=0, columnspan=2, sticky="w", padx=8, pady=6)
        v_folder = BooleanVar(value=self.cfg.get("playlist_in_folder", False))
        tb.Checkbutton(frame, text="Put playlists in their own folders", variable=v_folder, command=lambda: self._save("playlist_in_folder", v_folder.get())) \
            .grid(row=row, column=2, columnspan=2, sticky="w", padx=8, pady=6)

        tb.Separator(frame).grid(row=row+1, column=0, columnspan=4, sticky="ew", padx=8, pady=10)
        row += 2

        tb.Label(frame, text="Path to yt-dlp:").grid(row=row, column=0, sticky="w", padx=8, pady=6)
        var_ytdlp = StringVar(value=self.cfg.get("ytdlp_path", ""))
        ent_ytdlp = tb.Entry(frame, textvariable=var_ytdlp, state="readonly")
        ent_ytdlp.grid(row=row, column=1, columnspan=3, sticky="ew", padx=8, pady=6)
        ent_ytdlp.bind("<Button-1>", lambda e: self._select_executable(var_ytdlp, "ytdlp_path", "Select yt-dlp executable"))
        row += 1

        tb.Label(frame, text="FFmpeg folder:").grid(row=row, column=0, sticky="w", padx=8, pady=6)
        var_ffmpeg = StringVar(value=self.cfg.get("ffmpeg_path", ""))
        ent_ffmpeg = tb.Entry(frame, textvariable=var_ffmpeg, state="readonly")
        ent_ffmpeg.grid(row=row, column=1, columnspan=3, sticky="ew", padx=8, pady=6)
        ent_ffmpeg.bind("<Button-1>", lambda e: self._select_folder(var_ffmpeg, "ffmpeg_path", "Select FFmpeg Folder"))
        row += 1

        tb.Separator(frame).grid(row=row, column=0, columnspan=4, sticky="ew", padx=8, pady=10)
        row += 1

        v_proxy = BooleanVar(value=self.cfg.get("use_proxy", False))
        cb_proxy = tb.Checkbutton(frame, text="Use this proxy:", variable=v_proxy, command=lambda: self._save("use_proxy", v_proxy.get()))
        cb_proxy.grid(row=row, column=0, sticky="w", padx=8, pady=6)
        var_proxy = StringVar(value=self.cfg.get("proxy_url", ""))
        ent_proxy = tb.Entry(frame, textvariable=var_proxy)
        ent_proxy.grid(row=row, column=1, columnspan=3, sticky="ew", padx=8, pady=6)
        ent_proxy.bind("<FocusOut>", lambda e: self._save("proxy_url", var_proxy.get()))
        row += 1

        tb.Label(frame, text="Load cookies from browser:").grid(row=row, column=0, sticky="w", padx=8, pady=6)
        browsers = ["none", "brave", "chrome", "chromium", "edge", "firefox", "opera", "safari", "vivaldi"]
        var_browser = StringVar(value=self.cfg.get("cookies_from_browser", "none"))
        dd_browser = tb.Combobox(frame, textvariable=var_browser, values=browsers, state="readonly", width=10)
        dd_browser.grid(row=row, column=1, sticky="w", padx=8, pady=6)
        dd_browser.bind("<<ComboboxSelected>>", lambda e: self._save("cookies_from_browser", var_browser.get()))
        row += 1
        
        tb.Label(frame, text="Load cookies from file:").grid(row=row, column=0, sticky="w", padx=8, pady=6)
        var_cookie_file = StringVar(value=self.cfg.get("cookie_file_path", ""))
        ent_cookie_file = tb.Entry(frame, textvariable=var_cookie_file, state="readonly")
        ent_cookie_file.grid(row=row, column=1, columnspan=3, sticky="ew", padx=8, pady=6)
        ent_cookie_file.bind("<Button-1>", lambda e: self._select_cookie_file(var_cookie_file, "cookie_file_path"))
        row += 1

        v_keep = BooleanVar(value=self.cfg.get("keep_video", True))
        tb.Checkbutton(frame, text="Keep video (if remuxing)", variable=v_keep, command=lambda: self._save("keep_video", v_keep.get())).grid(row=row, column=0, sticky="w", padx=8)
        row += 1

    def _select_folder(self, var, key, title):
        initial_dir = "."
        if self.cfg.get("ui_browse_start_path") == "current":
            current_path = var.get()
            if Path(current_path).is_dir():
                initial_dir = current_path

        folder = filedialog.askdirectory(title=title, initialdir=initial_dir)
        if folder:
            var.set(folder)
            self._save(key, folder)

    def _select_cookie_file(self, var, key):
        filetypes = [("Text files", "*.txt"), ("All files", "*.*")]
        file_path = filedialog.askopenfilename(title="Select cookie file", filetypes=filetypes)
        if file_path:
            var.set(file_path)
            self._save(key, file_path)

    def _select_executable(self, var, key, title):
        if is_windows():
            filetypes = [("Executable files", "*.exe"), ("All files", "*.*")]
        else:
            filetypes = [("All files", "*.*")]
        
        file_path = filedialog.askopenfilename(
            title=title,
            filetypes=filetypes
        )
        if file_path:
            var.set(file_path)
            self._save(key, file_path)

    def _build_sponsorblock(self, frame):
        top_frame = tb.Frame(frame)
        top_frame.pack(fill=X, padx=8, pady=8)
        sb_link = tb.Label(top_frame, text="SponsorBlock", cursor="hand2", foreground=self.style.colors.primary)
        sb_link.pack(side=LEFT)
        sb_link.bind("<Button-1>", lambda e: webbrowser.open("https://sponsor.ajay.app/"))
        tb.Label(top_frame, text="lets users mark or remove segments in YouTube videos").pack(side=LEFT)

        content_frame = tb.Frame(frame)
        content_frame.pack(fill=BOTH, expand=True, padx=8, pady=4)
        content_frame.columnconfigure(0, weight=1)
        content_frame.columnconfigure(1, weight=1)

        v_enable = BooleanVar(value=self.cfg.get("sb_enable", False))
        def _upd_enable(*_): self._save("sb_enable", v_enable.get())
        tb.Checkbutton(content_frame, text="Enable SponsorBlock", variable=v_enable, command=_upd_enable)\
            .grid(row=0, column=0, sticky="w", padx=8, pady=8, columnspan=2)

        segments = [
            ("Sponsor", "sponsor"), ("Intermission/Intro Animation", "intro"), ("Endcards/Credits (Outro)", "outro"),
            ("Unpaid/Self Promotion", "selfpromo"), ("Preview/Recap", "preview"), ("Filler Tangent/Jokes", "filler"),
            ("Interaction Reminder (Subscribe)", "interaction"), ("Music: Non-Music Section", "music_offtopic"),
            ("Highlight", "poi_highlight"), ("Chapter", "chapter")
        ]
        
        mark_frame = tb.Labelframe(content_frame, text="Mark these categories:")
        mark_frame.grid(row=1, column=0, sticky=NSEW, padx=8, pady=8)
        
        mark_vars = {}
        mark_all_var = BooleanVar()

        def _toggle_mark_all():
            is_checked = mark_all_var.get()
            new_list = [k for _, k in segments] if is_checked else []
            self._save("sb_mark", new_list)
            for key, var in mark_vars.items(): var.set(is_checked)

        tb.Checkbutton(mark_frame, text="All", variable=mark_all_var, command=_toggle_mark_all).pack(anchor="w", padx=6, pady=2)
        
        for label, key in segments:
            v = BooleanVar(value=(key in self.cfg.get("sb_mark", [])))
            cb = tb.Checkbutton(mark_frame, text=label, variable=v, command=lambda k=key, var=v: self._toggle_in_list("sb_mark", k, var.get()))
            cb.pack(anchor="w", padx=16, pady=2)
            mark_vars[key] = v

        remove_frame = tb.Labelframe(content_frame, text="Remove these categories:")
        remove_frame.grid(row=1, column=1, sticky=NSEW, padx=8, pady=8)

        rem_vars = {}
        rem_all_var = BooleanVar()

        def _toggle_rem_all():
            is_checked = rem_all_var.get()
            new_list = [k for _, k in segments] if is_checked else []
            self._save("sb_remove", new_list)
            for key, var in rem_vars.items(): var.set(is_checked)

        tb.Checkbutton(remove_frame, text="All", variable=rem_all_var, command=_toggle_rem_all).pack(anchor="w", padx=6, pady=2)

        for label, key in segments:
            v = BooleanVar(value=(key in self.cfg.get("sb_remove", [])))
            cb = tb.Checkbutton(remove_frame, text=label, variable=v, command=lambda k=key, var=v: self._toggle_in_list("sb_remove", k, var.get()))
            cb.pack(anchor="w", padx=16, pady=2)
            rem_vars[key] = v

    def _build_queueing(self, frame):
        frame.columnconfigure(1, weight=1)
        row=0
        f_max_dl = tb.Frame(frame)
        f_max_dl.grid(row=row, column=0, columnspan=2, sticky="w", padx=8, pady=8)
        tb.Label(f_max_dl, text="Max concurrent downloads:").pack(side=LEFT, anchor="w")
        var_con = IntVar(value=self.cfg.get("queue_max_concurrent", 1))
        sb_con = tb.Spinbox(f_max_dl, from_=1, to=10, textvariable=var_con, width=5, command=lambda: self._save("queue_max_concurrent", var_con.get()))
        sb_con.pack(side=LEFT, padx=6)
        sb_con.bind("<FocusOut>", lambda e: self._save("queue_max_concurrent", var_con.get()))
        
        v_start_len = BooleanVar(value=self.cfg.get("queue_start_on_lengthy", True))
        tb.Checkbutton(f_max_dl, text="Start next item on lengthy processing", variable=v_start_len, command=lambda: self._save("queue_start_on_lengthy", v_start_len.get())).pack(side=LEFT, padx=10)
        row += 1

        f_max_data = tb.Frame(frame)
        f_max_data.grid(row=row, column=0, columnspan=2, sticky="w", padx=8, pady=8)
        tb.Label(f_max_data, text="Max number of concurrent yt-dlp instances used for getting data:").pack(side=LEFT, anchor="w")
        var_data = IntVar(value=self.cfg.get("queue_max_data_instances", 4))
        sb_data = tb.Spinbox(f_max_data, from_=1, to=10, textvariable=var_data, width=5, command=lambda: self._save("queue_max_data_instances", var_data.get()))
        sb_data.pack(side=LEFT, padx=6)
        sb_data.bind("<FocusOut>", lambda e: self._save("queue_max_data_instances", var_data.get()))
        row += 1

        v_autostart_stop = BooleanVar(value=self.cfg.get("queue_autostart_on_stop", False))
        tb.Checkbutton(frame, text="When stopping a queue item, automatically start the next one", variable=v_autostart_stop, command=lambda: self._save("queue_autostart_on_stop", v_autostart_stop.get())).grid(row=row, column=0, columnspan=2, sticky="w", padx=8, pady=4)
        row += 1

        v_item_opts = BooleanVar(value=self.cfg.get("queue_item_has_own_options", True))
        tb.Checkbutton(frame, text="Each queue item has its own download options", variable=v_item_opts, command=lambda: self._save("queue_item_has_own_options", v_item_opts.get())).grid(row=row, column=0, columnspan=2, sticky="w", padx=8, pady=4)
        row += 1

        v_autostart_launch = BooleanVar(value=self.cfg.get("queue_autostart_on_launch", False))
        tb.Checkbutton(frame, text="When the program starts, automatically start processing the queue", variable=v_autostart_launch, command=lambda: self._save("queue_autostart_on_launch", v_autostart_launch.get())).grid(row=row, column=0, columnspan=2, sticky="w", padx=8, pady=4)
        row += 1

        v_save_error = BooleanVar(value=self.cfg.get("queue_save_error_items", False))
        tb.Checkbutton(frame, text='Save queue items with "error" status to the settings file', variable=v_save_error, command=lambda: self._save("queue_save_error_items", v_save_error.get())).grid(row=row, column=0, columnspan=2, sticky="w", padx=8, pady=4)
        row += 1

        v_remove_done = BooleanVar(value=self.cfg.get("queue_remove_done_items", False))
        tb.Checkbutton(frame, text='Automatically remove completed items (with "done" status)', variable=v_remove_done, command=lambda: self._save("queue_remove_done_items", v_remove_done.get())).grid(row=row, column=0, columnspan=2, sticky="w", padx=8, pady=4)
        row += 1

        v_paste_activate = BooleanVar(value=self.cfg.get("queue_paste_on_activate", False))
        tb.Checkbutton(frame, text="When the main window is activated, automatically add the URL from clipboard", variable=v_paste_activate, command=lambda: self._save("queue_paste_on_activate", v_paste_activate.get())).grid(row=row, column=0, columnspan=2, sticky="w", padx=8, pady=4)
        row += 1
        
        tb.Separator(frame).grid(row=row, column=0, columnspan=2, sticky="ew", padx=8, pady=10)
        row += 1

        tb.Label(frame, text="Retry count:").grid(row=row, column=0, sticky="w", padx=8, pady=8)
        var_ret = StringVar(value=str(self.cfg.get("queue_retry", 2)))
        ent_ret = tb.Entry(frame, textvariable=var_ret, width=10)
        ent_ret.grid(row=row, column=1, sticky="w", padx=8, pady=8)
        ent_ret.bind("<FocusOut>", lambda e: self._save("queue_retry", max(0, int(var_ret.get() or "0"))))
        row += 1

        tb.Label(frame, text="Retry sleep (sec):").grid(row=row+1, column=0, sticky="w", padx=8, pady=8)
        var_slp = StringVar(value=str(self.cfg.get("queue_retry_sleep", 5)))
        ent_slp = tb.Entry(frame, textvariable=var_slp, width=10)
        ent_slp.grid(row=row+1, column=1, sticky="w", padx=8, pady=8)
        ent_slp.bind("<FocusOut>", lambda e: self._save("queue_retry_sleep", max(0, int(var_slp.get() or "0"))))

    def _build_interface(self, frame):
        frame.columnconfigure(1, weight=1)
        row = 0

        theme_frame = tb.Frame(frame)
        theme_frame.grid(row=row, column=0, columnspan=2, sticky="w", padx=8, pady=8)
        tb.Label(theme_frame, text="Color theme:").pack(side=LEFT, anchor="w")
        var_theme = StringVar(value=self.cfg.get("ui_theme", "system"))
        def _apply_theme():
            self._save("ui_theme", var_theme.get())
            if self.theme_apply_cb:
                self.theme_apply_cb(var_theme.get())
        tb.Radiobutton(theme_frame, text="Dark", value="dark", variable=var_theme, command=_apply_theme).pack(side=LEFT, padx=6)
        tb.Radiobutton(theme_frame, text="Light", value="light", variable=var_theme, command=_apply_theme).pack(side=LEFT, padx=6)
        tb.Radiobutton(theme_frame, text="System preference", value="system", variable=var_theme, command=_apply_theme).pack(side=LEFT, padx=6)
        row += 1

        tb.Separator(frame).grid(row=row, column=0, columnspan=2, sticky="ew", padx=8, pady=10)
        row += 1

        v_snap = BooleanVar(value=self.cfg.get("ui_snap_windows", True))
        tb.Checkbutton(frame, text="Snap windows to screen edges", variable=v_snap, command=lambda: self._save("ui_snap_windows", v_snap.get())).grid(row=row, column=0, columnspan=2, sticky="w", padx=8, pady=4)
        row += 1
        
        v_no_min = BooleanVar(value=self.cfg.get("ui_no_min_width", False))
        def _toggle_min_width():
            val = v_no_min.get()
            self._save("ui_no_min_width", val)
            self.master_window.apply_min_width()
        tb.Checkbutton(frame, text="No minimum width for the main window", variable=v_no_min, command=_toggle_min_width).grid(row=row, column=0, columnspan=2, sticky="w", padx=8, pady=4)
        row += 1

        v_exact_fs = BooleanVar(value=self.cfg.get("ui_exact_filesize", False))
        tb.Checkbutton(frame, text="Formats window: display file sizes with exact byte value", variable=v_exact_fs, command=lambda: self._save("ui_exact_filesize", v_exact_fs.get())).grid(row=row, column=0, columnspan=2, sticky="w", padx=8, pady=4)
        row += 1

        browse_frame = tb.Frame(frame)
        browse_frame.grid(row=row, column=0, columnspan=2, sticky="w", padx=8, pady=8)
        tb.Label(browse_frame, text="When browsing for the output folder, start in:").pack(side=LEFT, anchor="w")
        var_browse = StringVar(value=self.cfg.get("ui_browse_start_path", "current"))
        tb.Radiobutton(browse_frame, text="Currently selected folder", value="current", variable=var_browse, command=lambda: self._save("ui_browse_start_path", var_browse.get())).pack(side=LEFT, padx=6)
        tb.Radiobutton(browse_frame, text="Program folder", value="program", variable=var_browse, command=lambda: self._save("ui_browse_start_path", var_browse.get())).pack(side=LEFT, padx=6)
        row += 1

    def _build_updater(self, frame):
        frame.columnconfigure(1, weight=1)

        if_frame = tb.Labelframe(frame, text="ytdlp-interface")
        if_frame.pack(fill=X, padx=8, pady=4, ipady=4)
        if_frame.columnconfigure(1, weight=1)

        self.if_version_var = StringVar(value=f"Latest version: {APP_VERSION} (current)")
        tb.Label(if_frame, textvariable=self.if_version_var).grid(row=0, column=0, sticky="w", padx=8)
        tb.Button(if_frame, text="Release notes", command=self._open_releases).grid(row=0, column=1, sticky="e", padx=8)
        
        v_check_startup = BooleanVar(value=self.cfg.get("upd_check_on_start", False))
        tb.Checkbutton(if_frame, text="Check at program startup and display any new version in the title bar", variable=v_check_startup, command=lambda: self._save("upd_check_on_start", v_check_startup.get())).grid(row=1, column=0, columnspan=2, sticky="w", padx=8, pady=4)
        
        v_only_exe = BooleanVar(value=self.cfg.get("upd_only_extract_exe", True))
        tb.Checkbutton(if_frame, text="Only extract ytdlp-interface.exe from the downloaded archive", variable=v_only_exe, command=lambda: self._save("upd_only_extract_exe", v_only_exe.get())).grid(row=2, column=0, columnspan=2, sticky="w", padx=8, pady=4)
        
        update_if_frame = tb.Frame(if_frame)
        update_if_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=8, pady=4)
        tb.Button(update_if_frame, text="Update", command=self._update_interface).pack(side=LEFT)
        self.if_status_var = StringVar()
        tb.Label(update_if_frame, textvariable=self.if_status_var).pack(side=LEFT, padx=8)

        dep_frame = tb.Labelframe(frame, text="ffmpeg & yt-dlp")
        dep_frame.pack(fill=X, padx=8, pady=8, ipady=4)
        dep_frame.columnconfigure(0, weight=1)

        self.ytdlp_version_var = StringVar(value="Latest yt-dlp version: checking...")
        self.ffmpeg_version_var = StringVar(value="Latest ffmpeg version: checking...")
        tb.Label(dep_frame, textvariable=self.ytdlp_version_var).grid(row=0, column=0, columnspan=2, sticky="w", padx=8, pady=2)
        tb.Label(dep_frame, textvariable=self.ffmpeg_version_var).grid(row=1, column=0, columnspan=2, sticky="w", padx=8, pady=2)

        channel_frame = tb.Frame(dep_frame)
        channel_frame.grid(row=2, column=0, columnspan=2, sticky="w", padx=8, pady=4)
        tb.Label(channel_frame, text="yt-dlp release channel:").pack(side=LEFT)
        var_channel = StringVar(value=self.cfg.get("upd_ytdlp_channel", "stable"))
        tb.Radiobutton(channel_frame, text="Stable", value="stable", variable=var_channel, command=lambda: self._save("upd_ytdlp_channel", var_channel.get())).pack(side=LEFT, padx=6)
        tb.Radiobutton(channel_frame, text="Nightly", value="nightly", variable=var_channel, command=lambda: self._save("upd_ytdlp_channel", var_channel.get())).pack(side=LEFT, padx=6)

        v_ffplay = BooleanVar(value=self.cfg.get("upd_extract_ffplay", False))
        tb.Checkbutton(dep_frame, text='When updating ffmpeg, also extract "ffplay.exe"', variable=v_ffplay, command=lambda: self._save("upd_extract_ffplay", v_ffplay.get())).grid(row=3, column=0, columnspan=2, sticky="w", padx=8, pady=4)
        
        self.dep_status_var = StringVar()
        tb.Label(dep_frame, textvariable=self.dep_status_var).grid(row=4, column=0, columnspan=2, sticky="w", padx=8, pady=2)

        btn_frame = tb.Frame(frame)
        btn_frame.pack(fill=X, padx=8, pady=8)
        tb.Button(btn_frame, text="Update yt-dlp", command=self._update_yt_dlp).pack(side=RIGHT, padx=(4,0))
        tb.Button(btn_frame, text="Update Ffmpeg", command=self._update_ffmpeg_threaded).pack(side=RIGHT)

        self._check_all_versions()

    def _check_all_versions(self):
        threading.Thread(target=self._check_interface_version_thread, daemon=True).start()
        threading.Thread(target=self._check_ytdlp_version_thread, daemon=True).start()
        threading.Thread(target=self._check_ffmpeg_version_thread, daemon=True).start()

    def _check_interface_version_thread(self):
        if not requests: return
        self.if_version_var.set("Latest version: checking...")
        try:
            resp = requests.get(REPO_RELEASES_URL.replace("github.com", "api.github.com/repos") + "/latest", timeout=10)
            if resp.status_code == 200:
                latest = resp.json()["tag_name"].lstrip('v')
                status = "(current)" if latest == APP_VERSION else f"(new: {latest})"
                self.if_version_var.set(f"Latest version: {APP_VERSION} {status}")
            else:
                self.if_version_var.set(f"Latest version: {APP_VERSION} (check failed)")
        except Exception:
            self.if_version_var.set(f"Latest version: {APP_VERSION} (check failed)")

    def _check_ytdlp_version_thread(self):
        if not requests: return
        self.ytdlp_version_var.set("Latest yt-dlp version: checking...")
        try:
            current = self._get_yt_dlp_version()
            current_str = f"current = {current}" if current else "current = not present"
            
            resp = requests.get("https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest", timeout=10)
            if resp.status_code == 200:
                latest = resp.json()["tag_name"]
                self.ytdlp_version_var.set(f"Latest yt-dlp version: {latest} ({current_str})")
            else:
                self.ytdlp_version_var.set(f"Latest yt-dlp version: check failed ({current_str})")
        except Exception:
            self.ytdlp_version_var.set(f"Latest yt-dlp version: check failed")

    def _check_ffmpeg_version_thread(self):
        if not requests: return
        self.ffmpeg_version_var.set("Latest ffmpeg version: checking...")
        try:
            current = self.ffmpeg_updater.get_ffmpeg_version()
            current_str = f"current = {current}" if current else "current = not present"

            latest = self.ffmpeg_updater.get_latest_ffmpeg_version()
            if latest:
                self.ffmpeg_version_var.set(f"Latest ffmpeg version: {latest} ({current_str})")
            else:
                self.ffmpeg_version_var.set(f"Latest ffmpeg version: check failed ({current_str})")
        except Exception:
             self.ffmpeg_version_var.set(f"Latest ffmpeg version: check failed")
    
    def _update_interface(self):
        Messagebox.show_info("Manual Update Required", "Please visit the releases page to download the latest version.", parent=self)

    def _build_about(self, frame):
        frame.columnconfigure(0, weight=1)

        def _open_link(url):
            webbrowser.open(url)

        title_font = ("Segoe UI", 18, "bold", "italic")
        tb.Label(frame, text=APP_NAME, font=title_font).pack(pady=(10, 0))

        bit_system = "64-bit" if "64" in platform.architecture()[0] else "32-bit"
        tb.Label(frame, text=f"v{APP_VERSION} ({bit_system})").pack()

        original_link = tb.Label(frame, text=ORIGINAL_REPO_URL, cursor="hand2", foreground=self.style.colors.primary)
        original_link.pack()
        original_link.bind("<Button-1>", lambda e: _open_link(ORIGINAL_REPO_URL))
        tb.Label(frame, text="(Original C++ Project)").pack()

        port_link = tb.Label(frame, text=REPO_RELEASES_URL, cursor="hand2", foreground=self.style.colors.primary)
        port_link.pack(pady=(4,0))
        port_link.bind("<Button-1>", lambda e: _open_link(REPO_RELEASES_URL))
        tb.Label(frame, text="(This Python Port)").pack()

        tb.Separator(frame).pack(fill=X, padx=20, pady=15)
        
        tb.Label(frame, text="☆ Script Presets ☆", font="-weight bold").pack()
        tb.Label(frame, text="Based on TheFrenchGhosty's Ultimate YouTube-DL Scripts Collection").pack()
        ghosty_link = tb.Label(frame, text=GHOSTY_REPO_URL, cursor="hand2", foreground=self.style.colors.primary)
        ghosty_link.pack()
        ghosty_link.bind("<Button-1>", lambda e: _open_link(GHOSTY_REPO_URL))
        
        tb.Separator(frame).pack(fill=X, padx=20, pady=15)

        tb.Label(frame, text="☆ Libraries used ☆", font="-weight bold").pack()
        libs_frame = tb.Frame(frame)
        libs_frame.pack(pady=5)
        
        try: tb_ver = tb.__version__
        except Exception: tb_ver = "N/A"
        try: req_ver = requests.__version__
        except Exception: req_ver = "N/A"

        libraries = { "Python": platform.python_version(), "ttkbootstrap": tb_ver, "requests": req_ver, "Pillow": pil_ver or "N/A" }
        for lib, ver in libraries.items():
            text = f"{lib}: {ver}" if ver else lib
            tb.Label(libs_frame, text=text).pack()

        tb.Separator(frame).pack(fill=X, padx=20, pady=15)

        tb.Label(frame, text="☆ Keyboard shortcuts ☆", font="-weight bold").pack()
        keys_frame = tb.Frame(frame)
        keys_frame.pack(pady=5)
        
        shortcuts = {
            "Ctrl+S": "Settings",
            "Ctrl+F": "Formats",
            "Ctrl+Tab": "Switch view (queue/output)",
            "Ctrl+V": "Paste URL",
            "F2": "Set file name of queue item",
            "Delete": "Delete queue item(s)",
            "Ctrl+Num0": "Reset window size and position",
            "Esc": "Close window"
        }
        for i, (key, desc) in enumerate(shortcuts.items()):
            tb.Label(keys_frame, text=f"{key}:").grid(row=i, column=0, padx=10, sticky="e")
            tb.Label(keys_frame, text=desc).grid(row=i, column=1, padx=10, sticky="w")
            
    def _save(self, key, value):
        self.cfg[key] = value
        self.cfg.save()

    def _toggle_in_list(self, key, item, enabled: bool):
        lst = list(self.cfg.get(key, []))
        if enabled and item not in lst:
            lst.append(item)
        if not enabled and item in lst:
            lst.remove(item)
        self._save(key, lst)

    def _open_releases(self):
        try:
            webbrowser.open(REPO_RELEASES_URL)
        except Exception:
            pass

    def _get_yt_dlp_version(self):
        try:
            ytdlp_exe = self.cfg.get("ytdlp_path") or "yt-dlp"
            proc = subprocess.run([ytdlp_exe, "--version"], capture_output=True, text=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW if is_windows() else 0)
            if proc.returncode == 0:
                return proc.stdout.strip()
        except Exception:
            pass
        return None

    def _update_yt_dlp(self):
        try:
            ytdlp_exe = self.cfg.get("ytdlp_path") or "yt-dlp"
            cmd = [ytdlp_exe, "-U"]
            if self.cfg.get("upd_ytdlp_channel") == "nightly":
                cmd.append("--nightly")
            
            proc = subprocess.run(cmd, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW if is_windows() else 0)
            if proc.returncode == 0:
                Messagebox.show_info(proc.stdout or "yt-dlp updated successfully.", title="Update yt-dlp", parent=self)
            else:
                Messagebox.show_error(proc.stderr or "Failed to update yt-dlp.", title="Update yt-dlp", parent=self)
        except FileNotFoundError:
            Messagebox.show_error("yt-dlp not found in PATH or custom path.", title="Update yt-dlp", parent=self)
        except Exception as e:
            Messagebox.show_error(f"Error updating yt-dlp: {e}", title="Update yt-dlp", parent=self)
        finally:
            self._check_ytdlp_version_thread()

    def _update_ffmpeg_threaded(self):
        progress_window = tb.Toplevel(self)
        progress_window.title("Updating ffmpeg")
        progress_window.geometry("400x150")
        progress_window.resizable(False, False)
        progress_window.transient(self)
        progress_window.grab_set()
        
        progress_window.geometry("+%d+%d" % (self.winfo_rootx() + 50, self.winfo_rooty() + 50))
        
        progress_label = tb.Label(progress_window, text="Checking ffmpeg...")
        progress_label.pack(pady=20)
        
        progress_bar = tb.Progressbar(progress_window, mode='indeterminate')
        progress_bar.pack(fill=X, padx=20, pady=10)
        progress_bar.start()
        
        def update_progress(message):
            progress_window.after(0, lambda: progress_label.config(text=message))
        
        def update_ffmpeg():
            try:
                self.ffmpeg_updater.set_progress_callback(update_progress)
                success = self.ffmpeg_updater.check_and_update_ffmpeg()
                
                progress_window.after(0, progress_window.destroy)
                if success:
                    self.after(0, lambda: Messagebox.show_info("ffmpeg updated successfully!", title="Update Complete", parent=self))
                else:
                    self.after(0, lambda: Messagebox.show_error("Failed to update ffmpeg. Check console for details.", title="Update Failed", parent=self))
            except Exception as e:
                progress_window.after(0, progress_window.destroy)
                self.after(0, lambda: Messagebox.show_error(f"Error updating ffmpeg: {e}", title="Update Error", parent=self))
            finally:
                self._check_ffmpeg_version_thread()
        
        threading.Thread(target=update_ffmpeg, daemon=True).start()

def get_theme_name(pref: str) -> str:
    pref = (pref or "system").lower()
    if pref == "dark": return "darkly"
    if pref == "light": return "flatly"
    if is_macos(): return "flatly"
    return "darkly"

class App(tb.Window):
    def __init__(self, cfg: Config):
        self.cfg = cfg
        super().__init__(themename=get_theme_name(self.cfg.get("ui_theme", "system")))
        
        self._auto_detect_dependencies()
        
        self.title(APP_NAME)
        self.geometry("1100x700")
        self.apply_min_width()
        self.favicon_cache = {}
        self.youtube_photo_icon = None
        self.queue_data = {}

        self.download_queue = pyqueue.Queue()
        self.active_downloads = 0
        self._stop_event = threading.Event()
        self.last_clipboard_content = ""
        self.view_mode = 'queue'
        
        self.runner = Runner(on_log=self._on_runner_log, on_task=self._on_runner_task)

        self.style.configure("Custom.Treeview.Heading", borderwidth=1, relief="solid", padding=(4, 8))
        self.tree_style_name = "Custom.Treeview"
        self.style.configure(self.tree_style_name, rowheight=25)
        self.style.map(self.tree_style_name, background=[('selected', self.style.colors.primary)])
        
        self.main_view_frame = tb.Frame(self)
        self.main_view_frame.pack(side=TOP, fill=BOTH, expand=True, padx=8, pady=(8, 4))

        columns = ["#", "|", "Website", "Media title", "Status", "Format", "Format note", "Ext", "Filesize"]
        self.tree = tb.Treeview(self.main_view_frame, columns=columns, show="headings", height=14, style=self.tree_style_name)
        
        self.tree.tag_configure('oddrow', background=self.style.colors.get('bg'))
        self.tree.tag_configure('evenrow', background=self.style.colors.get('light'))

        self.column_widths = {"#": 40, "|": 30, "Website": 120, "Status": 160, "Format": 120, "Format note": 140, "Ext": 70, "Filesize": 90}
        
        for col, w in self.column_widths.items():
            self.tree.column(col, width=w, stretch=False, anchor="w")
            self.tree.heading(col, text=col)
        self.tree.column("Media title", stretch=True, anchor="w")
        self.tree.heading("Media title", text="Media title")
        self.tree.column("|", anchor="center")

        self._apply_column_visibility()

        placeholder_color = self.style.colors.get("primary")
        placeholder_text = "output from yt-dlp.exe appears here\n\nright-click for options\n\ndouble-click to show queue"
        self.placeholder_label = tb.Label(self.main_view_frame, text=placeholder_text, foreground=placeholder_color, justify="center", anchor="center")
        self.placeholder_label.bind("<Double-Button-1>", self._switch_view)

        self.output_console = ScrolledText(self.main_view_frame, autohide=True, wrap="word")
        self.output_console.text.config(state=DISABLED)
        self.output_console.text.bind("<Double-Button-1>", self._switch_view)

        self.tree.pack(fill=BOTH, expand=True)

        self.console_menu = tb.Menu(self, tearoff=False)
        self.v_highlight = BooleanVar(value=self.cfg.get("console_keyword_highlighting", True))
        self.v_limit_buffer = BooleanVar(value=self.cfg.get("console_limited_buffer", True))
        
        self.console_menu.add_command(label="Copy to clipboard", command=self._copy_from_console)
        self.console_menu.add_separator()
        self.console_menu.add_checkbutton(label="Keyword highlighting", variable=self.v_highlight, command=lambda: self._save("console_keyword_highlighting", self.v_highlight.get()))
        self.console_menu.add_checkbutton(label="Limited buffer size", variable=self.v_limit_buffer, command=lambda: self._save("console_limited_buffer", self.v_limit_buffer.get()))
        
        self.output_console.text.bind("<Button-3>", self._show_console_menu)
        self.placeholder_label.bind("<Button-3>", self._show_console_menu)

        self.bar = tb.Frame(self, bootstyle="dark")
        self.bar.pack(side=TOP, fill=X, padx=8, pady=(0, 6), ipady=4)
        self.bar.grid_columnconfigure(2, weight=1)

        btn_settings = tb.Button(self.bar, text="Settings", command=self._open_settings, bootstyle="light")
        btn_settings.grid(row=0, column=0, padx=(4, 4), pady=4)
        
        sep1 = tb.Separator(self.bar, orient='vertical')
        sep1.grid(row=0, column=1, sticky="ns", padx=4)
        
        self.url_var = StringVar()
        self.entry_url = tb.Entry(self.bar, textvariable=self.url_var)
        self.entry_url.grid(row=0, column=2, sticky="ew", padx=4, pady=4)
        self.placeholder_text = "Press Ctrl + V or click here to paste and add media link"
        self._set_placeholder()

        self.entry_url.bind("<FocusIn>", self._clear_placeholder)
        self.entry_url.bind("<FocusOut>", self._set_placeholder)
        self.entry_url.bind("<Button-1>", self._paste_and_add)
        self.entry_url.bind("<Button-3>", self._paste_and_add)


        self.btn_start = tb.Button(self.bar, text="Start download", command=self._start_download, bootstyle="success")
        self.btn_start.grid(row=0, column=3, padx=4, pady=4)

        sep2 = tb.Separator(self.bar, orient='vertical')
        sep2.grid(row=0, column=4, sticky="ns", padx=4)

        self._menu = tb.Menu(self, tearoff=False)
        self.btn_queue_actions = tb.Menubutton(self.bar, text="Queue actions", menu=self._menu, bootstyle="light")
        self.btn_queue_actions.grid(row=0, column=5, padx=(4, 4), pady=4)
        self.btn_queue_actions.bind("<Button-1>", self._update_queue_actions_menu)


        options_container = tb.Frame(self)
        options_container.pack(side=BOTTOM, fill=X, padx=8, pady=(0, 8))

        options_notebook = tb.Notebook(options_container)
        options_notebook.pack(fill=X, expand=True, pady=5)

        tab_basic = tb.Frame(options_notebook, padding=10)
        options_notebook.add(tab_basic, text="Download Options")

        tb.Label(tab_basic, text="Download folder:").grid(row=0, column=0, sticky="w", padx=(8,0))
        self.var_folder = StringVar(value=self.cfg.get("download_folder"))
        ent_folder = tb.Entry(tab_basic, textvariable=self.var_folder, state="readonly")
        ent_folder.grid(row=0, column=1, columnspan=5, sticky="ew", padx=8, pady=4)
        ent_folder.bind("<Button-1>", lambda e: self._pick_folder())
        
        tb.Label(tab_basic, text="Download rate limit:").grid(row=1, column=0, sticky="w", padx=(8,0), pady=4)
        self.rateval = StringVar(value=self.cfg.get("rate_limit_value", ""))
        self.rateunit = StringVar(value=self.cfg.get("rate_limit_unit", "MB/s"))
        rate_frame = tb.Frame(tab_basic)
        rate_frame.grid(row=1, column=1, sticky="w", padx=8)
        ent_rate = tb.Entry(rate_frame, textvariable=self.rateval, width=8)
        ent_rate.pack(side=LEFT)
        dd_unit = tb.Combobox(rate_frame, values=["KB/s", "MB/s"], textvariable=self.rateunit, width=5, state="readonly")
        dd_unit.pack(side=LEFT, padx=4)
        def _update_rate(*_):
            self._save("rate_limit_value", self.rateval.get())
            self._save("rate_limit_unit", self.rateunit.get())
        ent_rate.bind("<FocusOut>", _update_rate)
        dd_unit.bind("<<ComboboxSelected>>", _update_rate)

        self.v_mod = BooleanVar(value=self.cfg.get("file_mod_write_time"))
        tb.Checkbutton(tab_basic, text="File modification time = time of writing", variable=self.v_mod, command=lambda: self._save("file_mod_write_time", self.v_mod.get())).grid(row=1, column=2, columnspan=2, sticky="w", padx=4)
        
        self.v_subs = BooleanVar(value=self.cfg.get("embed_subtitles"))
        tb.Checkbutton(tab_basic, text="Embed subtitles", variable=self.v_subs, command=lambda: self._save("embed_subtitles", self.v_subs.get())).grid(row=1, column=4, sticky="w", padx=4)

        tb.Label(tab_basic, text="Chapters:").grid(row=2, column=0, sticky="w", padx=(8,0), pady=4)
        self.chapval = StringVar(value=self.cfg.get("chapter_mode"))
        chapters_lbl = ["Ignore", "Embedded", "Split"]
        chapters_val = ["ignore", "embedded", "split"]
        dd_chap_val = StringVar(value=chapters_lbl[chapters_val.index(self.chapval.get())])
        dd_chap = tb.Combobox(tab_basic, values=chapters_lbl, textvariable=dd_chap_val, width=10, state="readonly")
        dd_chap.grid(row=2, column=1, sticky="w", padx=8)
        def _update_chap(event=None):
            v = dd_chap.get()
            idx = chapters_lbl.index(v) if v in chapters_lbl else 0
            self._save("chapter_mode", chapters_val[idx])
        dd_chap.bind("<<ComboboxSelected>>", _update_chap)

        self.v_keyf = BooleanVar(value=self.cfg.get("force_keyframes"))
        tb.Checkbutton(tab_basic, text="Force keyframes at cuts", variable=self.v_keyf, command=lambda: self._save("force_keyframes", self.v_keyf.get())).grid(row=2, column=2, sticky="w", padx=4)

        self.v_thumb = BooleanVar(value=self.cfg.get("embed_thumbnail"))
        tb.Checkbutton(tab_basic, text="Embed thumbnail", variable=self.v_thumb, command=lambda: self._save("embed_thumbnail", self.v_thumb.get())).grid(row=2, column=3, sticky="w", padx=4)

        self.v_mp3 = BooleanVar(value=self.cfg.get("convert_to_mp3"))
        tb.Checkbutton(tab_basic, text="Convert audio to MP3", variable=self.v_mp3, command=lambda: self._save("convert_to_mp3", self.v_mp3.get())).grid(row=2, column=4, sticky="w", padx=4)

        self.v_custom = BooleanVar(value=bool(self.cfg.get("custom_args")))
        tb.Checkbutton(tab_basic, text="Custom arguments:", variable=self.v_custom).grid(row=3, column=0, sticky="w", padx=(8,0), pady=4)
        self.var_args = StringVar(value=self.cfg.get("custom_args"))
        ent_args = tb.Entry(tab_basic, textvariable=self.var_args)
        ent_args.grid(row=3, column=1, columnspan=5, sticky="ew", padx=8, pady=4)
        ent_args.bind("<FocusOut>", lambda e: self._save("custom_args", self.var_args.get()))

        for i in range(6): tab_basic.columnconfigure(i, weight=1)
        tab_basic.columnconfigure(0, weight=2)
        tab_basic.columnconfigure(1, weight=2)

        self.tab_advanced = tb.Frame(options_notebook, padding=10)
        options_notebook.add(self.tab_advanced, text="Advanced Scripts")
        
        self.tab_advanced.columnconfigure(1, weight=1)
        
        tb.Label(self.tab_advanced, text="Preset:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.preset_var = StringVar()

        all_presets = list_presets()
        filtered_presets = [p for p in all_presets if "No Comments" not in p]
        
        preset_dd = tb.Combobox(self.tab_advanced, textvariable=self.preset_var, values=filtered_presets, state="readonly")
        preset_dd.grid(row=0, column=1, columnspan=2, sticky="ew", padx=5, pady=5)
        
        if filtered_presets:
            preset_dd.set(filtered_presets[0])
            
        self.preset_var.trace_add("write", self._on_preset_change)

        self.adv_source_label = tb.Label(self.tab_advanced, text="Batch File:")
        self.adv_source_label.grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.adv_source_var = StringVar()
        adv_source_entry = tb.Entry(self.tab_advanced, textvariable=self.adv_source_var, state="readonly")
        adv_source_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        
        self.btn_select_source = tb.Button(self.tab_advanced, text="Select File", command=self._select_advanced_source)
        self.btn_select_source.grid(row=1, column=2, padx=5, pady=5)
        
        tb.Label(self.tab_advanced, text="Date Filter:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.date_filter_var = StringVar(value="None")
        date_filter_dd = tb.Combobox(self.tab_advanced, textvariable=self.date_filter_var, state="readonly",
                                     values=["None", "Last 24 hours", "Last 7 days", "Last 30 days", "Last 365 days"])
        date_filter_dd.grid(row=2, column=1, columnspan=2, sticky="ew", padx=5, pady=5)

        self.download_comments_var = BooleanVar(value=False)
        tb.Checkbutton(self.tab_advanced, text="Download Comments", variable=self.download_comments_var).grid(row=3, column=0, sticky="w", padx=5, pady=10)

        btn_run_script = tb.Button(self.tab_advanced, text="Run Script", command=self._run_advanced_script)
        btn_run_script.grid(row=3, column=1, columnspan=2, sticky="e", padx=5, pady=10)
        
        self._on_preset_change()

        self.actions_frame = tb.Frame(self)
        self.actions_frame.pack(side=BOTTOM, fill=X, padx=8, pady=8)
        self.btn_toggle_view = tb.Button(self.actions_frame, text="Show output", command=self._switch_view)
        self.btn_toggle_view.pack(side=RIGHT, padx=6)

        self.bind("<Control-v>", self._paste_and_add)
        self.bind("<Control-V>", self._paste_and_add)
        self.bind("<FocusIn>", self._handle_focus_in)
        self.bind("<Control-s>", lambda e: self._open_settings())
        self.bind("<Control-S>", lambda e: self._open_settings())
        self.bind("<Delete>", self._delete_selected_items)
        self.bind("<Control-f>", self._show_formats_placeholder)
        self.bind("<Control-F>", self._show_formats_placeholder)
        self.bind("<F2>", self._edit_queue_item_placeholder)
        self.bind("<Control-Tab>", self._switch_view)
        self.bind("<Control-Key-0>", self._reset_window_geometry)
        self.bind("<Control-KP_0>", self._reset_window_geometry)
        self.bind("<Configure>", self._on_resize)
        self.tree.bind("<Button-1>", self._prevent_column_resize)
        self.tree.bind("<Motion>", self._prevent_resize_cursor)
        self.tree.bind("<<TreeviewSelect>>", self._update_queue_actions_menu)
        self.tree.bind("<Button-3>", self._show_queue_context_menu)


        if self.cfg.get("upd_check_on_start", False):
            self.after(1000, self._check_ffmpeg_on_startup)

    def _auto_detect_dependencies(self):
        config_changed = False
        
        if getattr(sys, 'frozen', False):
            base_path = Path(sys.executable).parent
        else:
            base_path = Path(__file__).parent
        
        ytdlp_path_cfg = self.cfg.get("ytdlp_path")
        if not ytdlp_path_cfg or not Path(ytdlp_path_cfg).exists():
            potential_ytdlp_path = base_path / "yt-dlp.exe"
            if potential_ytdlp_path.exists():
                self.cfg["ytdlp_path"] = str(potential_ytdlp_path)
                config_changed = True

        ffmpeg_path_cfg = self.cfg.get("ffmpeg_path")
        if not ffmpeg_path_cfg or not Path(ffmpeg_path_cfg).exists():
            potential_ffmpeg_exe = base_path / "ffmpeg.exe"
            if potential_ffmpeg_exe.exists():
                self.cfg["ffmpeg_path"] = str(base_path)
                config_changed = True

        if config_changed:
            self.cfg.save()

    def _on_preset_change(self, *args):
        is_check_script = self.preset_var.get() == "Check Unavailability"
        if is_check_script:
            self.adv_source_label.config(text="Video Directory:")
            self.btn_select_source.config(text="Select Directory")
        else:
            self.adv_source_label.config(text="Batch File:")
            self.btn_select_source.config(text="Select File")
        self.adv_source_var.set("")

    def _select_advanced_source(self):
        is_check_script = self.preset_var.get() == "Check Unavailability"
        path = ""
        if is_check_script:
            path = filedialog.askdirectory(title="Select Video Directory")
        else:
            path = filedialog.askopenfilename(
                title="Select Batch File",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
            )
        if path:
            self.adv_source_var.set(path)

    def _on_runner_log(self, log_line: str):
        self.after(0, self._append_to_console, log_line)

    def _on_runner_task(self, task: Task):
        gui_id = getattr(task, 'gui_id', None)
        if gui_id:
            status_map = {
                "running": "Downloading...",
                "done": "Done",
                "error": f"Failed (rc={task.returncode})"
            }
            status_text = status_map.get(task.status, task.status)
            self.after(0, self._update_row_value, gui_id, "Status", status_text)
            
            if task.status == "done" and self.cfg.get("queue_remove_done_items", False):
                self.after(3000, lambda: self.tree.delete(gui_id))

    def _run_advanced_script(self):
        preset_name = self.preset_var.get()
        source_path = self.adv_source_var.get()

        if not preset_name:
            Messagebox.show_warning("Please select a preset.", "Advanced Script")
            return
        if not source_path:
            source_type = "Directory" if preset_name == "Check Unavailability" else "File"
            Messagebox.show_warning(f"Please select a source {source_type}.", "Advanced Script")
            return

        urls_to_process = []
        if preset_name == "Check Unavailability":
            id_pattern = re.compile(r'\[([a-zA-Z0-9_-]{11})\]')
            for root, _, files in os.walk(source_path):
                for name in files:
                    match = id_pattern.search(name)
                    if match:
                        video_id = match.group(1)
                        urls_to_process.append(f"https://www.youtube.com/watch?v={video_id}")
        else:
            try:
                with open(source_path, 'r', encoding='utf-8') as f:
                    urls_to_process = [line.strip() for line in f if line.strip()]
            except Exception as e:
                Messagebox.show_error(f"Failed to read batch file:\n{e}", "Advanced Script Error")
                return

        if not urls_to_process:
            Messagebox.showinfo("No URLs Found", "The source file or directory was empty or invalid.", parent=self)
            return

        base_args = preset_args(preset_name)
        
        try:
            batch_idx = base_args.index("--batch-file")
            base_args.pop(batch_idx)
            base_args.pop(batch_idx)
        except (ValueError, IndexError):
            pass

        if self.download_comments_var.get():
            base_args.append("--write-comments")

        date_filter = self.date_filter_var.get()
        if date_filter != "None":
            days = {"Last 24 hours": 1, "Last 7 days": 7, "Last 30 days": 30, "Last 365 days": 365}.get(date_filter)
            if days:
                date_after = datetime.now() - timedelta(days=days)
                base_args.extend(["--dateafter", date_after.strftime('%Y%m%d')])

        for url in urls_to_process:
            self._add_url_to_queue(url, preset_args=base_args)
        
        if self.view_mode == 'output':
            self._switch_view()

    def _prevent_resize_cursor(self, event):
        if self.tree.identify_region(event.x, event.y) == "separator":
            self.tree.config(cursor="arrow")
        else:
            self.tree.config(cursor="")

    def _prevent_column_resize(self, event):
        if self.tree.identify_region(event.x, event.y) == "separator":
            return "break"

    def _on_resize(self, event=None):
        self._adjust_column_widths()

    def _adjust_column_widths(self):
        visible_columns = self.tree['displaycolumns']
        if not visible_columns or '#0' in visible_columns:
             visible_columns = self.tree['columns']
        
        fixed_width_total = 0
        for col in visible_columns:
            if col != "Media title":
                fixed_width_total += self.tree.column(col, "width")

        padding = 25 
        title_width = self.tree.winfo_width() - fixed_width_total - padding
        
        if title_width > 50:
            self.tree.column("Media title", width=title_width)

    def _setup_queue_actions_menu(self):
        self._menu.delete(0, END)

        queue_has_items = bool(self.tree.get_children())
        selection = self.tree.selection()
        item_selected = bool(selection)
        
        if queue_has_items:
            state = NORMAL if item_selected else DISABLED
            item_num_str = self.tree.item(selection[0], "values")[0] if item_selected else "#"

            self._menu.add_command(label=f"Start item {item_num_str}", state=state)
            self._menu.add_command(label=f"Remove item {item_num_str}", state=state, command=self._delete_selected_items)
            self._menu.add_command(label=f"Open folder of item {item_num_str}", state=state)
            self._menu.add_command(label=f"Set file name of item {item_num_str}", state=state)
            self._menu.add_separator()
            self._menu.add_command(label="Download sections", state=state)
            self._menu.add_command(label="View JSON data", state=state)
            self._menu.add_command(label="Refresh (reacquire data)", state=state)
            self._menu.add_command(label="Do not download", state=state)
            self._menu.add_separator()
        
        extra_cols_menu = tb.Menu(self._menu, tearoff=False)
        self.extra_col_vars = {
            "Format": BooleanVar(value=self.cfg.get("show_format_col")),
            "Format note": BooleanVar(value=self.cfg.get("show_format_note_col")),
            "Ext": BooleanVar(value=self.cfg.get("show_ext_col")),
            "Filesize": BooleanVar(value=self.cfg.get("show_filesize_col")),
        }
        for name, var in self.extra_col_vars.items():
            key = f"show_{name.lower().replace(' ', '_')}_col"
            extra_cols_menu.add_checkbutton(label=name, variable=var, command=lambda k=key, v=var: self._toggle_and_save_col(k, v))
        self._menu.add_cascade(label="Extra columns", menu=extra_cols_menu)

        website_cols_menu = tb.Menu(self._menu, tearoff=False)
        self.website_col_vars = {
            "Favicon": BooleanVar(value=self.cfg.get("show_website_favicon_col")),
            "Text": BooleanVar(value=self.cfg.get("show_website_text_col")),
        }
        for name, var in self.website_col_vars.items():
            key = f"show_website_{name.lower()}_col"
            website_cols_menu.add_checkbutton(label=name, variable=var, command=lambda k=key, v=var: self._toggle_and_save_col(k, v))
        self._menu.add_cascade(label="Website column", menu=website_cols_menu)
        
        self._menu.add_separator()
        
        finish_menu = tb.Menu(self._menu, tearoff=False)
        self.finish_action = StringVar(value=self.cfg.get("finish_action", "none"))
        for key, lbl in [("none", "None"), ("shutdown", "Shutdown"), ("hibernate", "Hibernate"), ("sleep", "Sleep"), ("exit", "Exit app")]:
            finish_menu.add_radiobutton(label=lbl, value=key, variable=self.finish_action, command=self._save_finish_action)
        self._menu.add_cascade(label="When finished", menu=finish_menu)

    def _show_queue_context_menu(self, event):
        self._setup_queue_actions_menu()
        self._menu.post(event.x_root, event.y_root)

    def _update_queue_actions_menu(self, event=None):
        self._setup_queue_actions_menu()

    def _toggle_and_save_col(self, key, var):
        self._save(key, var.get())
        self._apply_column_visibility()

    def apply_min_width(self):
        if not self.cfg.get("ui_no_min_width", False):
            self.minsize(900, 600)
        else:
            self.minsize(1, 1)

    def _reset_window_geometry(self, event=None):
        default_width = 1100
        default_height = 700
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        center_x = (screen_width // 2) - (default_width // 2)
        center_y = (screen_height // 2) - (default_height // 2)
        self.geometry(f'{default_width}x{default_height}+{center_x}+{center_y}')

    def _show_formats_placeholder(self, event=None):
        Messagebox.show_info("Not Implemented", "The formats window is not yet available.")
        
    def _edit_queue_item_placeholder(self, event=None):
        Messagebox.show_info("Not Implemented", "Editing queue items with F2 is not yet available.")
        
    def _switch_view(self, event=None):
        if self.view_mode == 'queue':
            self.tree.pack_forget()
            self.bar.pack_forget() 
            self.view_mode = 'output'
            self.btn_toggle_view.config(text="Show queue")
            if len(self.output_console.get("1.0", END).strip()) > 0:
                self.output_console.pack(fill=BOTH, expand=True)
            else:
                self.placeholder_label.pack(fill=BOTH, expand=True)
        else:
            self.output_console.pack_forget()
            self.placeholder_label.pack_forget()
            self.view_mode = 'queue'
            self.btn_toggle_view.config(text="Show output")
            self.tree.pack(fill=BOTH, expand=True)
            self.bar.pack(side=TOP, fill=X, padx=8, pady=(0, 6), ipady=4)
    
    def _show_console_menu(self, event):
        self.console_menu.post(event.x_root, event.y_root)

    def _copy_from_console(self):
        self.clipboard_clear()
        self.clipboard_append(self.output_console.get("1.0", END))
    
    def _clear_console(self):
        self.output_console.text.config(state=NORMAL)
        self.output_console.delete("1.0", END)
        self.output_console.text.config(state=DISABLED)
        self.output_console.pack_forget()
        self.placeholder_label.pack(fill=BOTH, expand=True)

    def _append_to_console(self, text):
        if self.view_mode == 'output':
            self.placeholder_label.pack_forget()
            self.output_console.pack(fill=BOTH, expand=True)

        self.output_console.text.config(state=NORMAL)
        self.output_console.insert(END, text)
        self.output_console.see(END)
        self.output_console.text.config(state=DISABLED)

    def _handle_focus_in(self, event=None):
        if self.cfg.get("queue_paste_on_activate", False):
            self._paste_and_add()

    def _check_ffmpeg_on_startup(self):
        def check_ffmpeg():
            try:
                if not requests: return
                updater = FFmpegUpdater(self.cfg)
                if not updater.get_ffmpeg_version():
                    updater.check_and_update_ffmpeg()
            except Exception:
                pass
        
        threading.Thread(target=check_ffmpeg, daemon=True).start()

    def _pick_folder(self):
        initial_dir = "."
        if self.cfg.get("ui_browse_start_path") == "current":
            current_path = self.var_folder.get()
            if Path(current_path).is_dir():
                initial_dir = current_path
        
        folder = filedialog.askdirectory(title="Select Download Folder", initialdir=initial_dir)
        if folder:
            self.var_folder.set(folder)
            self._save("download_folder", folder)

    def _apply_column_visibility(self):
        columns = ["#"]
        if self.cfg.get("show_website_favicon_col"): columns.append("|")
        if self.cfg.get("show_website_text_col"): columns.append("Website")
        columns += ["Media title", "Status"]
        if self.cfg.get("show_format_col"): columns.append("Format")
        if self.cfg.get("show_format_note_col"): columns.append("Format note")
        if self.cfg.get("show_ext_col"): columns.append("Ext")
        if self.cfg.get("show_filesize_col"): columns.append("Filesize")
        self.tree["displaycolumns"] = columns
        self.after(50, self._adjust_column_widths)

    def _save_finish_action(self):
        self.cfg["finish_action"] = self.finish_action.get()
        self.cfg.save()

    def _apply_theme(self, pref: str):
        self.style.theme_use(get_theme_name(pref))

    def _open_settings(self):
        SettingsWindow(self, self.cfg, theme_apply_cb=self._apply_theme)

    def _set_placeholder(self, event=None):
        if not self.url_var.get():
            self.url_var.set(self.placeholder_text)
            self.entry_url.config(foreground="grey")

    def _clear_placeholder(self, event=None):
        if self.url_var.get() == self.placeholder_text:
            self.url_var.set("")
            self.entry_url.config(foreground=self.style.colors.get('fg'))

    def _show_temp_message(self, message):
        self._clear_placeholder()
        self.url_var.set(message)
        self.entry_url.config(foreground="orange")
        self.after(3000, self._set_placeholder)

    def _paste_and_add(self, event=None):
        self._clear_placeholder()
        try:
            url = self.clipboard_get().strip()
        except TclError:
            url = "" 
        
        if not url:
            self.after(50, lambda: self._show_temp_message("The clipboard does not contain any text."))
            return

        for item_id, item_data in self.queue_data.items():
            if item_data['url'] == url and self.tree.exists(item_id):
                item_num = self.tree.item(item_id, "values")[0]
                self._show_temp_message(f"The URL in the clipboard is already added (queue item #{item_num}).")
                return
        
        self.url_var.set(url)
        self.after(50, lambda: self._add_url_to_queue(self.url_var.get()))
        self.after(100, lambda: self.url_var.set(""))
        self.after(101, self._set_placeholder)
    
    def _add_url_to_queue(self, url, preset_args=None, metadata=None):
        idx = len(self.tree.get_children()) + 1
        domain = urlparse(url).netloc
        values = [idx, "", domain, url, "Fetching data...", "", "", "", ""]
        
        tag = 'oddrow' if idx % 2 == 1 else 'evenrow'
        iid = self.tree.insert("", "end", values=values, tags=(tag,))
        self.queue_data[iid] = {'url': url, 'json_data': None, 'preset_args': preset_args}
        
        if self.cfg.get("show_website_favicon_col"):
            self._fetch_and_set_favicon(iid, domain)
        
        if metadata:
            self.after(0, self._update_row_with_metadata, iid, metadata)
        else:
            threading.Thread(target=self._fetch_metadata, args=(iid, url), daemon=True).start()
        
        self._update_queue_actions_menu()

    def _fetch_metadata(self, iid, url):
        ytdlp_exe = self.cfg.get("ytdlp_path") or "yt-dlp"
        cmd = [ytdlp_exe, url, "--dump-json", "--no-warnings", "--no-playlist"]
        
        is_first_video = True
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', creationflags=subprocess.CREATE_NO_WINDOW if is_windows() else 0)
            
            for line in process.stdout:
                try:
                    json_data = json.loads(line)
                    if is_first_video:
                        self.after(0, self._update_row_with_metadata, iid, json_data)
                        is_first_video = False
                    else:
                        new_url = json_data.get("webpage_url", "")
                        preset_args = self.queue_data.get(iid, {}).get('preset_args')
                        self.after(0, self._add_url_to_queue, new_url, preset_args, metadata=json_data)
                except json.JSONDecodeError:
                    continue 
            
            stderr = process.communicate()[1]
            if is_first_video and stderr: 
                self.after(0, self._update_row_with_error, iid, "yt-dlp did not provide any data for this URL!")

        except Exception as e:
            self.after(0, self._update_row_with_error, iid, f"Error: {e}")

    def _update_row_with_metadata(self, iid, data):
        if not self.tree.exists(iid): return
        
        self.queue_data[iid]['json_data'] = data
        self.queue_data[iid]['url'] = data.get('webpage_url', self.queue_data[iid]['url'])
        
        title = data.get('title', 'N/A')
        format_id = data.get('format_id', '')
        format_note = data.get('format_note', data.get('resolution', ''))
        ext = data.get('ext', '')
        
        filesize = data.get('filesize_approx')
        if filesize:
            if filesize > 1024*1024*1024:
                filesize_str = f"~{filesize / (1024*1024*1024):.2f} GB"
            elif filesize > 1024*1024:
                filesize_str = f"~{filesize / (1024*1024):.2f} MB"
            else:
                filesize_str = f"~{filesize / 1024:.2f} KB"
        else:
            filesize_str = ""

        self._update_row_value(iid, "Media title", title)
        self._update_row_value(iid, "Status", "Queued")
        self._update_row_value(iid, "Format", format_id)
        self._update_row_value(iid, "Format note", format_note)
        self._update_row_value(iid, "Ext", ext)
        self._update_row_value(iid, "Filesize", filesize_str)

    def _update_row_with_error(self, iid, message):
        if not self.tree.exists(iid): return
        self._update_row_value(iid, "Media title", message)
        self._update_row_value(iid, "Status", "Error")

    def _update_row_value(self, iid, col_name, new_value):
        if not self.tree.exists(iid): return
        
        try:
            current_values = list(self.tree.item(iid, "values"))
            all_cols = self.tree["columns"]
            col_index = all_cols.index(col_name)
            current_values[col_index] = new_value
            self.tree.item(iid, values=current_values)
        except (ValueError, IndexError) as e:
            print(f"Error updating row {iid}: {e}")

    def _fetch_and_set_favicon(self, iid, domain):
        domain_lower = domain.lower()
        if 'youtube.com' in domain_lower or 'youtu.be' in domain_lower:
            try:
                if not self.youtube_photo_icon:
                    img_data = base64.b64decode(YOUTUBE_FAVICON_B64)
                    img = Image.open(io.BytesIO(img_data))
                    self.youtube_photo_icon = ImageTk.PhotoImage(img)
                
                if self.tree.exists(iid):
                    self.after(0, lambda: self.tree.item(iid, image=self.youtube_photo_icon))
            except Exception as e:
                print(f"Could not load embedded YouTube icon: {e}")
            return

        if domain in self.favicon_cache:
            if self.favicon_cache[domain] and self.tree.exists(iid):
                self.after(0, lambda: self.tree.item(iid, image=self.favicon_cache[domain]))
            return

        try:
            resp = requests.get(f"https://www.google.com/s2/favicons?domain={domain}&sz=16", timeout=10)
            if resp.status_code == 200 and resp.content:
                img_data = resp.content
                img = Image.open(io.BytesIO(img_data))
                photo_img = ImageTk.PhotoImage(img)
                self.favicon_cache[domain] = photo_img
                if self.tree.exists(iid):
                    self.after(0, lambda: self.tree.item(iid, image=photo_img))
            else:
                 self.favicon_cache[domain] = None
        except Exception as e:
            print(f"Could not fetch favicon for {domain}: {e}")
            self.favicon_cache[domain] = None

    def _delete_selected_items(self, event=None):
        selected_items = self.tree.selection()
        if not selected_items:
            return
        for item_id in selected_items:
            if self.tree.exists(item_id):
                if item_id in self.queue_data:
                    del self.queue_data[item_id]
                self.tree.delete(item_id)
        self._update_queue_actions_menu()

    def _start_download(self):
        selected_items = self.tree.selection()
        if not selected_items:
            selected_items = [iid for iid in self.tree.get_children() if self.tree.item(iid, "values")[4] == "Queued"]
            if not selected_items:
                Messagebox.show_warning("No items are queued for download.", "Start Download")
                return

        for iid in selected_items:
            if self.tree.exists(iid) and iid in self.queue_data:
                status = self.tree.item(iid, "values")[4]
                if status == "Queued":
                    item_data = self.queue_data[iid]
                    url = item_data['url']
                    preset_args = item_data.get('preset_args')

                    item_cfg = copy.deepcopy(self.cfg) if self.cfg.get("queue_item_has_own_options", True) else self.cfg
                    if preset_args:
                        item_cfg["download_folder"] = self.var_folder.get()

                    cmd = build_yt_dlp_cmd(item_cfg, url, preset_args)
                    
                    task = Task(label=url, cmd=cmd)
                    task.gui_id = iid
                    
                    self._update_row_value(iid, "Status", "Starting...")
                    self.runner.enqueue(task)

    def _queue_finished(self):
        action = self.cfg.get("finish_action", "none")
        if action == "none": return
        if action == "exit": self.after(200, self.quit)
        else: self.after(500, lambda: perform_finish_action(action))

    def _save(self, k, v):
        self.cfg[k] = v
        self.cfg.save()

def main():
    if is_windows():
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        base = Path.home() / ".config"
    cfg_path = base / APP_NAME / "config.json"
    
    cfg = Config(cfg_path)
    
    app = App(cfg)
    app.mainloop()

if __name__ == "__main__":
    main()