import { useRef, useEffect, useState } from 'react';
import { saveAudioWithDialog } from '../saveAudio';

const INSTRUMENT_EMOJI = {
  piano: '🎹', guitar: '🎸', bass: '🎸', drums: '🥁',
  violin: '🎻', cello: '🎻', flute: '🪈', trumpet: '🎺',
  synth_pad: '🌊', synth_lead: '🎹', hulusi: '🎵',
};

const COLORS = {
  piano: '#58a6ff', guitar: '#d29922', bass: '#3fb950', drums: '#f85149',
  violin: '#bc8cff', cello: '#f778ba', flute: '#39d2c0', trumpet: '#e8833a',
  synth_pad: '#58a6ff', synth_lead: '#bc8cff', hulusi: '#6e40aa',
};

function getCSSVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function TrackItem({ track, selected, onSelect, onVolumeChange, jobId }) {
  const canvasRef = useRef(null);
  const [playing, setPlaying] = useState(false);
  const [saveMsg, setSaveMsg] = useState('');
  const audioRef = useRef(null);
  const isVocal = track.role === 'vocal';

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const w = canvas.width = canvas.offsetWidth;
    const h = canvas.height = canvas.offsetHeight;
    const bgColor = getCSSVar('--bg-input') || '#0d1117';
    ctx.fillStyle = bgColor;
    ctx.fillRect(0, 0, w, h);
    const pinkColor = getCSSVar('--pink') || '#f778ba';
    const color = isVocal ? pinkColor : (COLORS[track.instrument] || '#58a6ff');
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    const bars = 80;
    for (let i = 0; i < bars; i++) {
      const x = (i / bars) * w;
      const seed = (track.id.charCodeAt(track.id.length - 1) || 0) + i;
      const amp = (Math.sin(seed * 0.7) * 0.3 + Math.sin(seed * 1.3) * 0.2 + Math.random() * 0.15 + 0.35) * (track.volume || 0.8);
      ctx.moveTo(x, h / 2 - amp * (h / 2 - 2));
      ctx.lineTo(x, h / 2 + amp * (h / 2 - 2));
    }
    ctx.stroke();
  }, [track, isVocal]);

  const togglePlay = (e) => {
    e.stopPropagation();
    if (!track.audio_url) return;
    if (playing && audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
      setPlaying(false);
    } else {
      const a = new Audio(track.audio_url);
      a.volume = track.volume || 0.8;
      a.onended = () => setPlaying(false);
      a.play();
      audioRef.current = a;
      setPlaying(true);
    }
  };

  const handleSave = async (e) => {
    e.stopPropagation();
    if (!track.audio_url || !jobId) return;
    const filename = track.audio_url.split('/').pop();
    const displayName = `${track.id}_${track.name}.wav`;
    setSaveMsg('保存中...');
    const result = await saveAudioWithDialog(jobId, filename, displayName);
    if (result.cancelled) { setSaveMsg(''); return; }
    if (result.success) {
      setSaveMsg(result.path === 'browser-download' ? '已下载' : `已保存`);
    } else {
      setSaveMsg(`失败: ${result.error}`);
    }
    setTimeout(() => setSaveMsg(''), 3000);
  };

  const emoji = isVocal ? '🎤' : (INSTRUMENT_EMOJI[track.instrument] || '🎵');

  return (
    <div className={`track-item ${selected ? 'selected' : ''}`} onClick={() => onSelect(track.id)}>
      <div className="track-header">
        <div
          className={`track-icon ${isVocal ? '' : 'instrument-' + track.instrument}`}
          style={isVocal ? { background: 'linear-gradient(135deg, #880e4f, #ad1457)' } : {}}
        >
          {emoji}
        </div>
        <div className="track-info">
          <h4>
            {track.name}
            {isVocal && <span style={{ fontSize: 11, color: 'var(--pink)', fontWeight: 400 }}> 人声</span>}
          </h4>
          <div className="track-meta">
            <span>{isVocal ? (track.voice || 'vocal') : (track.instrument || 'piano')}</span>
            <span>CH {track.channel}</span>
            <span>{track.part || 'melody'}</span>
            {track.note_count != null && <span>{track.note_count} 音符</span>}
          </div>
        </div>
        <div className="track-controls">
          <button className={playing ? 'playing' : ''} onClick={togglePlay}>
            {playing ? '⏸' : '▶'}
          </button>
          <input
            type="range"
            className="volume-slider"
            min="0"
            max="1"
            step="0.05"
            value={track.volume || 0.8}
            onChange={e => onVolumeChange(track.id, parseFloat(e.target.value))}
            onClick={e => e.stopPropagation()}
          />
          {track.audio_url && (
            <button
              className="btn btn-small"
              style={{ fontSize: 11, padding: '2px 8px', marginLeft: 4 }}
              onClick={handleSave}
              title={`保存 ${track.name}`}
            >
              💾
            </button>
          )}
          {saveMsg && (
            <span style={{ fontSize: 10, color: 'var(--success, #3fb950)', marginLeft: 4 }}>{saveMsg}</span>
          )}
        </div>
      </div>
      <div className="track-waveform">
        <canvas ref={canvasRef} className="waveform-canvas" />
      </div>
    </div>
  );
}

export default function TrackList({ tracks, selectedTrack, onSelect, onVolumeChange, jobId }) {
  return (
    <div className="track-list">
      {tracks.map(track => (
        <TrackItem
          key={track.id}
          track={track}
          selected={selectedTrack === track.id}
          onSelect={onSelect}
          onVolumeChange={onVolumeChange}
          jobId={jobId}
        />
      ))}
    </div>
  );
}