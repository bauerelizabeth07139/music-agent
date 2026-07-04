import { useState, useRef, useCallback } from 'react';

const VOICE_OPTIONS = [
  { value: '冰糖', label: '冰糖（甜美女声）' },
  { value: '茉莉', label: '茉莉（柔美女声）' },
  { value: '苏打', label: '苏打（清亮女声）' },
  { value: '白桦', label: '白桦（磁性男声）' },
  { value: 'mimo_default', label: '默认声音' },
  { value: 'Mia', label: 'Mia（英文女声）' },
  { value: 'Chloe', label: 'Chloe（英文女声2）' },
  { value: 'Milo', label: 'Milo（英文男声）' },
  { value: 'Dean', label: 'Dean（英文男声2）' },
];

const STYLE_OPTIONS = [
  { value: '', label: '自动（跟随音色）' },
  { value: '播音', label: '播音' },
  { value: '甜美', label: '甜美' },
  { value: '沉稳', label: '沉稳' },
  { value: '活力', label: '活力' },
  { value: '旁白', label: '旁白' },
  { value: '讲故事', label: '讲故事' },
];

export default function VoicePanel({ voiceMode, setVoiceMode, onSynth, onClone, loading }) {
  const [text, setText] = useState('');
  const [voice, setVoice] = useState('mimo_default');
  const [synthStyle, setSynthStyle] = useState('');
  const [audioUrl, setAudioUrl] = useState(null);
  const [file, setFile] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef(null);

  const handleSynth = async () => {
    if (!text.trim() || loading) return;
    const url = await onSynth(text.trim(), voice, synthStyle);
    if (url) setAudioUrl(url);
  };

  const handleClone = async () => {
    if (!text.trim() || !file || loading) return;
    const url = await onClone(text.trim(), file);
    if (url) setAudioUrl(url);
  };

  const handleDrop = useCallback(e => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files.length) setFile(e.dataTransfer.files[0]);
  }, []);

  return (
    <div className="voice-section">
      <div className="mode-tabs" style={{ alignSelf: 'flex-start' }}>
        <button className={`mode-tab ${voiceMode === 'synth' ? 'active' : ''}`}
          onClick={() => { setVoiceMode('synth'); setAudioUrl(null); }}>
          声音合成
        </button>
        <button className={`mode-tab ${voiceMode === 'clone' ? 'active' : ''}`}
          onClick={() => { setVoiceMode('clone'); setAudioUrl(null); }}>
          声音克隆（歌手）
        </button>
      </div>

      <div className="voice-input-area">
        <label style={{ fontSize: 13, color: '#8b949e' }}>
          {voiceMode === 'clone' ? '输入歌词' : '输入文本'}
        </label>
        <textarea
          value={text}
          onChange={e => setText(e.target.value)}
          placeholder={voiceMode === 'clone' ? '输入歌词...' : '输入要合成的文本...'}
        />
      </div>

      {voiceMode === 'synth' ? (
        <>
          <div style={{ display: 'flex', gap: 12 }}>
            <div className="config-field" style={{ flex: 1 }}>
              <label>声音角色</label>
              <select value={voice} onChange={e => setVoice(e.target.value)}>
                {VOICE_OPTIONS.map(v => (
                  <option key={v.value} value={v.value}>{v.label}</option>
                ))}
              </select>
            </div>
            <div className="config-field" style={{ flex: 1 }}>
              <label>风格</label>
              <select value={synthStyle} onChange={e => setSynthStyle(e.target.value)}>
                {STYLE_OPTIONS.map(s => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>
            </div>
          </div>
          <button className="btn btn-primary" onClick={handleSynth}
            disabled={loading || !text.trim()} style={{ alignSelf: 'flex-start' }}>
            {loading ? '合成中...' : '开始合成'}
          </button>
        </>
      ) : (
        <>
          <p style={{ fontSize: 12, color: '#8b949e', margin: 0 }}>
            上传声音样本，MiMo 克隆该声线并演唱歌词
          </p>
          <div
            className={`drop-zone ${dragOver ? 'drag-over' : ''}`}
            onClick={() => fileInputRef.current?.click()}
            onDrop={handleDrop}
            onDragOver={e => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
          >
            <span className="icon">🎤</span>
            {file ? (
              <div className="file-info" style={{ marginTop: 12, display: 'inline-flex' }}>
                <span className="name">{file.name}</span>
                <span style={{ color: '#8b949e', fontSize: 11 }}>
                  ({(file.size / 1024).toFixed(1)} KB)
                </span>
                <button className="btn btn-small btn-danger"
                  onClick={e => { e.stopPropagation(); setFile(null); }}>✕</button>
              </div>
            ) : (
              <p style={{ margin: '8px 0 0' }}>点击或拖拽音频文件（WAV/MP3/FLAC）</p>
            )}
            <input
              ref={fileInputRef}
              type="file"
              accept="audio/*"
              style={{ display: 'none' }}
              onChange={e => { if (e.target.files.length) setFile(e.target.files[0]); }}
            />
          </div>
          <button className="btn btn-primary" onClick={handleClone}
            disabled={loading || !text.trim() || !file} style={{ alignSelf: 'flex-start' }}>
            {loading ? '克隆并演唱中...' : '克隆声音并演唱'}
          </button>
        </>
      )}

      {audioUrl && (
        <div style={{ marginTop: 'auto' }}>
          <h4 style={{ margin: '0 0 12px', fontSize: 13, color: '#8b949e', textTransform: 'uppercase', letterSpacing: 0.5 }}>
            输出结果
          </h4>
          <div className="audio-player">
            <audio controls src={audioUrl} style={{ width: '100%' }} />
          </div>
        </div>
      )}
    </div>
  );
}

