import { useRef, useState } from 'react';

export default function MasterPlayer({ masterUrl, multitrackUrl, arrangement, tracks }) {
  const [playing, setPlaying] = useState(false);
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

  const downloadAllTracks = () => {
    if (!tracks || tracks.length === 0) return;
    tracks.forEach((t, i) => {
      if (!t.audio_url) return;
      const a = document.createElement('a');
      a.href = t.audio_url;
      a.download = `${t.id}_${t.name}.wav`;
      a.style.display = 'none';
      document.body.appendChild(a);
      setTimeout(() => { a.click(); document.body.removeChild(a); }, i * 300);
    });
  };

  const trackCount = tracks ? tracks.length : 0;
  const vocalCount = tracks ? tracks.filter(t => t.role === 'vocal').length : 0;
  const instCount = trackCount - vocalCount;

  return (
    <div className="master-section">
      <h4>🎧 混音总线（Master Mix）</h4>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center', marginBottom: 10 }}>
        <span style={{ fontSize: 12, color: var(--text-muted) }}>
          {trackCount} 条音轨（{vocalCount} 人声 · {instCount} 乐器）
        </span>
      </div>
      <div className="audio-player">
        <button className={`btn ${playing ? 'btn-danger' : 'btn-primary'}`} onClick={togglePlay}>
          {playing ? '⏸ 停止' : '▶ 播放全部'}
        </button>
        <audio controls src={masterUrl} style={{ flex: 1 }} />
      </div>
      <div style={{ display: 'flex', gap: 8, marginTop: 10, flexWrap: 'wrap' }}>
        <a
          href={masterUrl}
          download="master_mix.wav"
          className="btn"
          style={{ textDecoration: 'none' }}
        >
          💾 下载混音 (master_mix.wav)
        </a>
        {multitrackUrl && (
          <a
            href={multitrackUrl}
            download="multitrack.wav"
            className="btn"
            style={{ textDecoration: 'none' }}
          >
            🎛️ 下载多轨文件 (multitrack.wav)
          </a>
        )}
        <button className="btn" onClick={downloadAllTracks}>
          📦 下载全部分轨 ({trackCount} 个文件)
        </button>
      </div>
      <p style={{ fontSize: 11, color: var(--text-muted), marginTop: 8, lineHeight: 1.5 }}>
        • <b>混音文件</b>：所有音轨叠加为一个立体声 WAV<br/>
        • <b>多轨文件</b>：每条音轨占一个独立声道（可导入 DAW 分轨编辑）<br/>
        • <b>分轨文件</b>：每条音轨单独下载为独立 WAV
      </p>
    </div>
  );
}

