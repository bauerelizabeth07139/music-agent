/**
 * Audio save utility -- uses native OS dialog when available,
 * falls back to browser download.
 */

function isDesktopApp() {
  return typeof window !== 'undefined' && window.pywebview && window.pywebview.api;
}

export async function saveAudioWithDialog(jobId, filename, displayName) {
  if (isDesktopApp()) {
    try {
      const savePath = await window.pywebview.api.save_file_dialog(displayName || filename);
      if (!savePath) return { success: false, cancelled: true };
      const sep = savePath.lastIndexOf('\\\\') !== -1 ? '\\\\' : '/';
      const dir = savePath.substring(0, savePath.lastIndexOf(sep));
      const resp = await fetch('/api/save-audio', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_id: jobId, filename: filename, save_dir: dir }),
      });
      const data = await resp.json();
      if (data.success) return { success: true, path: data.path };
      return { success: false, error: data.detail || 'Save failed' };
    } catch (e) {
      console.error('Native save failed:', e);
      return { success: false, error: e.message };
    }
  } else {
    // Browser: try folder picker via backend, then fallback to download
    try {
      const resp = await fetch('/api/browse-folder');
      if (resp.ok) {
        const { path: folder } = await resp.json();
        const saveResp = await fetch('/api/save-audio', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ job_id: jobId, filename: filename, save_dir: folder }),
        });
        const data = await saveResp.json();
        if (data.success) return { success: true, path: data.path };
      }
    } catch (e) {
      // Folder picker may not work, fall through
    }
    // Final fallback: direct browser download
    const a = document.createElement('a');
    a.href = '/api/audio/' + jobId + '/' + filename;
    a.download = displayName || filename;
    a.style.display = 'none';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    return { success: true, path: 'browser-download' };
  }
}

export async function saveAllTracksWithDialog(jobId, filenames) {
  if (isDesktopApp()) {
    try {
      const folder = await window.pywebview.api.browse_folder();
      if (!folder) return { success: false, cancelled: true };
      const resp = await fetch('/api/save-all-tracks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_id: jobId, filename: '*', save_dir: folder }),
      });
      return await resp.json();
    } catch (e) {
      return { success: false, error: e.message };
    }
  } else {
    try {
      const browseResp = await fetch('/api/browse-folder');
      if (browseResp.ok) {
        const { path: folder } = await browseResp.json();
        const resp = await fetch('/api/save-all-tracks', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ job_id: jobId, filename: '*', save_dir: folder }),
        });
        return await resp.json();
      }
    } catch (e) {
      // Fall through
    }
    // Final fallback: sequential browser downloads
    if (!filenames || filenames.length === 0) return { success: false };
    filenames.forEach((f, i) => {
      const a = document.createElement('a');
      a.href = f.audio_url;
      a.download = f.id + '_' + f.name + '.wav';
      a.style.display = 'none';
      document.body.appendChild(a);
      setTimeout(() => { a.click(); document.body.removeChild(a); }, i * 300);
    });
    return { success: true, count: filenames.length, path: 'browser-download' };
  }
}
