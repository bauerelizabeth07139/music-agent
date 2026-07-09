import { useRef, useState } from 'react';
import { saveAudioWithDialog, saveAllTracksWithDialog } from '../saveAudio';

export default function MasterPlayer({ masterUrl, multitrackUrl, arrangement, tracks, jobId }) {
  const [playing, setPlaying] = useState(false);
  const [saveMsg, setSaveMsg] = useState('');
  const audioRef = useRef(null);

  const togglePlay = () => {
    if (!masterUrl) return;
    if (playing && audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
      setPlaying(false);
    } else {
      const audio = new Audio(masterUrl);
      audio.onended = () => setPlaying(false);
      audio.play();
      audioRef.current = audio;
      setPlaying(true);
    }
  };

  const showMsg = (msg) => {
    setSaveMsg(msg);
    setTimeout(() => setSaveMsg(''), 4000);
  };

  const handleSaveMaster = async () => {
    if (!jobId || !masterUrl) return;
    const filename = masterUrl.split('/').pop();
    const result = await saveAudioWithDialog(jobId, filename, 'master_mix.wav');
    if (result.cancelled) return;
    if (result.success) {
      showMsg(result.path === 'browser-download' ? '已开始下载' : `已保存到: ${result.path}`);
    } else {
      showMsg(`保存失败: ${result.error}`);
    }
  };

  const handleSaveMultitrack = async () => {
    if (!jobId || !multitrackUrl) return;
    const filename = multitrackUrl.split('/').pop();
    const result = await saveAudioWithDialog(jobId, filename, 'multitrack.wav');
    if (result.cancelled) return;
    if (result.success) {
      showMsg(result.path === 'browser-download' ? '已开始下载' : `已保存到: ${result.path}`);
    } else {
      showMsg(`保存失败: ${result.error}`);
    }
  };

  const handleSaveAll = async () => {
    if (!jobId || !tracks) return;
    const result = await saveAllTracksWithDialog(jobId, tracks);
    if (result.cancelled) return;
    if (result.success) {
      showMsg(result.path === 'browser-download'
        ? `已开始下载 ${result.count} 个文件`
        : `已保存 ${result.count} 个文件到: ${result.path}`);
    } else {
      showMsg(`保存失败: ${result.error}`);
    }
  };

  const trackCount = tracks ? tracks.length : 0;
  const vocalCount = tracks ? tracks.filter(t => t.role === 'vocal').length : 0;
  const instCount = trackCount - vocalCount;

  return (
    <div className="master-section">
      <h4>🎧 混音总线（Master Mix）</h4>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center', marginBottom: 10 }}>
        <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
          {trackCount} 条音轨（{vocalCount} 人声 · {instCount} 乐器）
        </span>
      </div>
      <div className="audio-player">
        <button className={`btn ${playing ? 'btn-danger' : 'btn-primary'}`} onClick={togglePlay}>
          {playing ? '⏸ 停止' : '▶ 播放全部'}
        </button>
        <audio controls src={masterUrl} style={{ flex: 1 }} />
      </div>
      <div style={{ display: 'flex', gap: 8, marginTop: 10, flexWrap: 'wrap', alignItems: 'center' }}>
        <button className="btn" onClick={handleSaveMaster}>
          💾 保存混音 (master_mix.wav)
        </button>
        {multitrackUrl && (
          <button className="btn" onClick={handleSaveMultitrack}>
            🎛️ 保存多轨文件 (multitrack.wav)
          </button>
        )}
        <button className="btn" onClick={handleSaveAll}>
          📦 保存全部分轨 ({trackCount} 个文件)
        </button>
      </div>
      {saveMsg && (
        <div style={{ fontSize: 12, color: 'var(--success, #3fb950)', marginTop: 8, padding: '4px 8px', background: 'rgba(63,185,80,0.1)', borderRadius: 4 }}>
          {saveMsg}
        </div>
      )}
      <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 8, lineHeight: 1.5 }}>
        • <b>混音文件</b>：所有音轨叠加为一个立体声 WAV<br/>
        • <b>多轨文件</b>：每条音轨占一个独立声道（可导入 DAW 分轨编辑）<br/>
        • <b>分轨文件</b>：每条音轨单独保存为独立 WAV，点击后弹出文件夹选择框
      </p>
    </div>
  );
}