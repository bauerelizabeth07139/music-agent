import { useState } from 'react';

const STYLE_OPTIONS = [
  { value: '', label: '风格（可选）' },
  { value: 'pop', label: '流行' },
  { value: 'rock', label: '摇滚' },
  { value: 'jazz', label: '爵士' },
  { value: 'classical', label: '古典' },
  { value: 'electronic', label: '电子' },
  { value: 'hiphop', label: '嘻哈' },
  { value: 'rnb', label: 'R&B' },
  { value: 'folk', label: '民谣' },
  { value: 'cinematic', label: '电影配乐' },
  { value: 'country', label: '乡村' },
  { value: 'blues', label: '蓝调' },
];

const VOICE_OPTIONS = [
  { value: '冰糖', label: '冰糖（甜美女声·推荐演唱）' },
  { value: '茉莉', label: '茉莉（柔美女声）' },
  { value: '苏打', label: '苏打（清亮女声）' },
  { value: '白桦', label: '白桦（磁性男声·推荐男唱）' },
  { value: 'mimo_default', label: '默认声音' },
  { value: 'Mia', label: 'Mia（英文女声）' },
  { value: 'Chloe', label: 'Chloe（英文女声2）' },
  { value: 'Milo', label: 'Milo（英文男声）' },
  { value: 'Dean', label: 'Dean（英文男声2）' },
];

const INSTRUMENT_OPTIONS = [
  { value: 'piano', label: '钢琴' },
  { value: 'guitar', label: '吉他' },
  { value: 'bass', label: '贝斯' },
  { value: 'drums', label: '鼓' },
  { value: 'violin', label: '小提琴' },
  { value: 'cello', label: '大提琴' },
  { value: 'flute', label: '长笛' },
  { value: 'trumpet', label: '小号' },
  { value: 'synth_pad', label: '合成铺底' },
  { value: 'synth_lead', label: '合成领奏' },
  { value: 'hulusi', label: '葫芦丝' },
];

const PART_OPTIONS = [
  { value: 'melody', label: '旋律' },
  { value: 'harmony', label: '和声' },
  { value: 'bass', label: '低音' },
  { value: 'drums', label: '鼓组' },
  { value: 'accompaniment', label: '伴奏' },
  { value: 'lead', label: '领奏' },
  { value: 'pad', label: '铺底' },
];

const TIME_SIGS = ['4/4', '3/4', '6/8', '2/4', '5/4', '7/8'];

// ---------- Track Editor ----------
function TrackEditor({ tracks, onUpdate, onAdd, onRemove }) {
  return (
    <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: 8, padding: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>音轨配置</span>
        <button className="btn btn-small" onClick={onAdd}>+ 添加音轨</button>
      </div>
      <p style={{ fontSize: 11, color: 'var(--text-muted)', margin: '0 0 12px' }}>
        自由配置音轨，AI 也会自动增删。不一定要人声。
      </p>
      {tracks.map((t, i) => (
        <div key={t.id} style={{ display: 'flex', gap: 6, alignItems: 'center', marginBottom: 8, padding: '8px 10px', background: 'var(--bg-input)', border: '1px solid var(--border)', borderRadius: 6, flexWrap: 'wrap' }}>
          <span style={{ fontSize: 11, color: 'var(--text-muted)', minWidth: 18 }}>#{i + 1}</span>
          <input type="text" value={t.name} onChange={e => onUpdate(t.id, 'name', e.target.value)}
            style={{ width: 80, padding: '4px 6px', background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: 4, color: 'var(--text-primary)', fontSize: 12 }} />
          <select value={t.role} onChange={e => onUpdate(t.id, 'role', e.target.value)}
            style={{ padding: '4px 6px', background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: 4, color: 'var(--text-primary)', fontSize: 12 }}>
            <option value="vocal">人声</option>
            <option value="instrument">乐器</option>
          </select>
          {t.role === 'vocal' ? (
            <select value={t.voice} onChange={e => onUpdate(t.id, 'voice', e.target.value)}
              style={{ padding: '4px 6px', background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: 4, color: 'var(--text-primary)', fontSize: 12 }}>
              {VOICE_OPTIONS.map(v => <option key={v.value} value={v.value}>{v.label}</option>)}
            </select>
          ) : (
            <select value={t.instrument} onChange={e => onUpdate(t.id, 'instrument', e.target.value)}
              style={{ padding: '4px 6px', background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: 4, color: 'var(--text-primary)', fontSize: 12 }}>
              {INSTRUMENT_OPTIONS.map(v => <option key={v.value} value={v.value}>{v.label}</option>)}
            </select>
          )}
          <select value={t.part} onChange={e => onUpdate(t.id, 'part', e.target.value)}
            style={{ padding: '4px 6px', background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: 4, color: 'var(--text-primary)', fontSize: 12 }}>
            {PART_OPTIONS.map(v => <option key={v.value} value={v.value}>{v.label}</option>)}
          </select>
          <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>CH{t.channel}</span>
          <button className="btn btn-small btn-danger" onClick={() => onRemove(t.id)}
            style={{ padding: '2px 6px', fontSize: 10 }}>✕</button>
        </div>
      ))}
    </div>
  );
}

// ---------- Rhythm Editor ----------
function RhythmEditor({ bpm, setBpm, timeSignature, setTimeSignature, songKey, setSongKey }) {
  return (
    <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: 8, padding: 16 }}>
      <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', display: 'block', marginBottom: 12 }}>
        节奏与调性（参考，AI 可自行调整）
      </span>
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
        <div style={{ flex: '1 1 120px' }}>
          <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>BPM</label>
          <input type="number" min="40" max="240" value={bpm} onChange={e => setBpm(parseInt(e.target.value) || 100)}
            style={{ width: '100%', padding: '6px 8px', background: 'var(--bg-input)', border: '1px solid var(--border)', borderRadius: 4, color: 'var(--text-primary)', fontSize: 13 }} />
        </div>
        <div style={{ flex: '1 1 120px' }}>
          <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>拍号</label>
          <select value={timeSignature} onChange={e => setTimeSignature(e.target.value)}
            style={{ width: '100%', padding: '6px 8px', background: 'var(--bg-input)', border: '1px solid var(--border)', borderRadius: 4, color: 'var(--text-primary)', fontSize: 13 }}>
            {TIME_SIGS.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
        <div style={{ flex: '1 1 120px' }}>
          <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>调性</label>
          <input type="text" value={songKey} onChange={e => setSongKey(e.target.value)} placeholder="C major"
            style={{ width: '100%', padding: '6px 8px', background: 'var(--bg-input)', border: '1px solid var(--border)', borderRadius: 4, color: 'var(--text-primary)', fontSize: 13 }} />
        </div>
      </div>
    </div>
  );
}

// ---------- Meta bar ----------
function MetaBar({ arrangement }) {
  if (!arrangement) return null;
  return (
    <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', fontSize: 12, color: 'var(--text-muted)', alignItems: 'center' }}>
      {arrangement.title && <span style={{ color: 'var(--info)', fontWeight: 600 }}>{arrangement.title}</span>}
      <span>{arrangement.bpm || '?'} BPM</span>
      <span>{arrangement.time_signature || '?'}</span>
      <span>{arrangement.key || '?'}</span>
      <span>{(arrangement.tracks || []).length} 音轨</span>
    </div>
  );
}

// ---------- Track Plan View ----------
function TrackPlanView({ plan, showNotes }) {
  if (!plan?.tracks) return null;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {plan.tracks.map((t, i) => {
        const noteCount = t.note_count || (t.notes ? t.notes.length : 0);
        return (
          <div key={t.id} style={{ display: 'flex', gap: 12, alignItems: 'center', padding: '10px 14px', background: 'var(--bg-input)', border: '1px solid var(--border)', borderRadius: 6 }}>
            <span style={{ fontSize: 18 }}>{t.role === 'vocal' ? '🎤' : '🎵'}</span>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>{t.name}</div>
              <div style={{ display: 'flex', gap: 8, marginTop: 4, flexWrap: 'wrap' }}>
                <span style={{ fontSize: 11, background: t.role === 'vocal' ? '#880e4f22' : '#1a237e22', color: t.role === 'vocal' ? 'var(--pink)' : 'var(--info)', padding: '2px 6px', borderRadius: 4 }}>
                  {t.role === 'vocal' ? '人声（TTS）' : '乐器（合成）'}
                </span>
                <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                  {t.role === 'vocal' ? (t.voice || 'singing_female') : (t.instrument || 'piano')}
                </span>
                <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{t.part || 'melody'}</span>
                <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>CH{t.channel ?? i}</span>
                {showNotes && noteCount > 0 && (
                  <span style={{ fontSize: 11, color: 'var(--success)' }}>{noteCount} 音符</span>
                )}
                {!showNotes && (
                  <span style={{ fontSize: 11, color: '#d29922' }}>待生成音符</span>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ---------- Main ArrangePanel ----------
export default function ArrangePanel({
  step, loading, style, setStyle,
  lyricsData, confirmedLyrics, setConfirmedLyrics,
  arrangement, notesArrangement, tracks, references,

  onGenerateLyrics, onConfirmLyrics, onConfirmPlan, onConfirmVocal, onConfirmNotes, onReset,
  onAddTrack, onRemoveTrack, onUpdateTrack
}) {
  const [prompt, setPrompt] = useState('');

  // Step 1: Input
  if (step === 'input') return (
    <div style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 16, flex: 1, overflow: 'auto' }}>
      <h3 style={{ margin: 0, fontSize: 16 }}>🎵 创作你的歌曲</h3>
      <div>
        <label style={{ fontSize: 13, color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>创意描述</label>
        <textarea value={prompt} onChange={e => setPrompt(e.target.value)}
          placeholder="描述你想要的歌曲...例如：写一首关于星空和爱情的抒情流行歌曲"
          style={{ width: '100%', minHeight: 100, padding: 12, background: 'var(--bg-input)', border: '1px solid var(--border)', borderRadius: 6, color: 'var(--text-primary)', fontSize: 14, resize: 'vertical', fontFamily: 'inherit' }} />
      </div>
      <div style={{ display: 'flex', gap: 12, alignItems: 'flex-end', flexWrap: 'wrap' }}>
        <div style={{ flex: '1 1 200px' }}>
          <label style={{ fontSize: 13, color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>音乐风格</label>
          <select value={style} onChange={e => setStyle(e.target.value)}
            style={{ width: '100%', padding: '8px 10px', background: 'var(--bg-input)', border: '1px solid var(--border)', borderRadius: 6, color: 'var(--text-primary)', fontSize: 14 }}>
            {STYLE_OPTIONS.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
          </select>
        </div>
      </div>
      <div style={{ background: "#161b22", border: "1px solid #30363d", borderRadius: 8, padding: 12, fontSize: 12, color: "#8b949e" }}>
        <span style={{ fontWeight: 600, color: "#e6edf3" }}>🎼 节奏与调性</span>：由 AI 根据风格自动决定
      </div>
      <TrackEditor tracks={tracks} onUpdate={onUpdateTrack} onAdd={onAddTrack} onRemove={onRemoveTrack} />
      <button className="btn btn-primary" onClick={() => onGenerateLyrics(prompt, style)} disabled={loading || !prompt.trim()}
        style={{ alignSelf: 'flex-start', padding: '10px 24px', fontSize: 14 }}>
        {loading ? '生成中...' : '✨ 生成歌词'}
      </button>
    </div>
  );

  // Step 2: Lyrics confirmation
  if (step === 'lyrics-voice') return (
    <div style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 16, flex: 1, overflow: 'auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3 style={{ margin: 0, fontSize: 16 }}>📝 歌词确认</h3>
        <button className="btn btn-small" onClick={onReset}>返回</button>
      </div>
      {lyricsData?.title && <div style={{ fontSize: 18, fontWeight: 600, color: 'var(--info)' }}>{lyricsData.title}</div>}
      {lyricsData?.sections && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {lyricsData.sections.map((s, i) => (
            <div key={i} style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: 6, padding: 12 }}>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 6 }}>{s.label || s.type}</div>
              <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontSize: 14, color: 'var(--text-primary)', fontFamily: 'inherit' }}>{s.lyrics}</pre>
            </div>
          ))}
        </div>
      )}
      <div>
        <label style={{ fontSize: 13, color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>完整歌词（可编辑）</label>
        <textarea value={confirmedLyrics} onChange={e => setConfirmedLyrics(e.target.value)}
          style={{ width: '100%', minHeight: 150, padding: 12, background: 'var(--bg-input)', border: '1px solid var(--border)', borderRadius: 6, color: 'var(--text-primary)', fontSize: 14, resize: 'vertical', fontFamily: 'inherit', lineHeight: 1.6 }} />
      </div>
      {references && references.results && references.results.length > 0 && (
        <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: 8, padding: 12 }}>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>参考信息</div>
          {references.results.slice(0, 3).map((r, i) => (
            <div key={i} style={{ fontSize: 12, color: 'var(--info)', marginBottom: 4 }}>
              {r.title || r.text || JSON.stringify(r)}
            </div>
          ))}
        </div>
      )}
      <button className="btn btn-primary" onClick={onConfirmLyrics} disabled={loading || !confirmedLyrics.trim()}
        style={{ alignSelf: 'flex-start', padding: '10px 24px', fontSize: 14 }}>
        {loading ? '生成人声中...' : '🎤 确认歌词和音色，生成人声'}
      </button>
    </div>
  );

  // Step 3: Plan confirmation (plan auto-generated after vocal TTS)
  if (step === 'plan-confirm' && arrangement) return (
    <div style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 16, flex: 1, overflow: 'auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3 style={{ margin: 0, fontSize: 16 }}>🎼 编曲规划</h3>
        <button className="btn btn-small" onClick={onReset}>返回</button>
      </div>
      <MetaBar arrangement={arrangement} />
      <p style={{ fontSize: 13, color: 'var(--success)', margin: 0 }}>✓ 人声已生成，编曲方案已基于人声时长自动规划</p>
      <TrackPlanView plan={arrangement} showNotes={false} />
      <button className="btn btn-primary" onClick={onConfirmPlan} disabled={loading}
        style={{ alignSelf: 'flex-start', padding: '10px 24px', fontSize: 14 }}>
        {loading ? '生成中...' : '🎹 确认规划，生成音符'}
      </button>
    </div>
  );

  // (vocal-confirm removed — voice is now picked in lyrics-voice step)

  // Step 5: Notes confirmation (notes generated - show actual counts)
  if (step === 'notes-confirm' && notesArrangement) {
    const totalNotes = (notesArrangement.tracks || []).reduce(
      (s, t) => s + (t.note_count || (t.notes || []).length || 0), 0
    );
    return (
      <div style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 16, flex: 1, overflow: 'auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3 style={{ margin: 0, fontSize: 16 }}>🎹 音符确认</h3>
          <button className="btn btn-small" onClick={onReset}>返回</button>
        </div>
        <MetaBar arrangement={notesArrangement} />
        <div style={{ fontSize: 13, color: 'var(--info)' }}>
          共 {notesArrangement.tracks?.length || 0} 条音轨，{totalNotes} 个音符
        </div>
        <TrackPlanView plan={notesArrangement} showNotes={true} />
        <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: 8, padding: 14, fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.6 }}>
          <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: 6 }}>🔊 渲染说明</div>
          <div>• 人声轨道：歌词已嵌入音符，将通过 <span style={{ color: 'var(--pink)' }}>MiMo TTS</span> 合成真实演唱</div>
          <div>• 乐器轨道：音符已生成，将通过 <span style={{ color: 'var(--info)' }}>合成引擎</span> 并行渲染</div>
          <div>• 所有轨道并行处理，人声优先启动</div>
        </div>
        <button className="btn btn-primary" onClick={onConfirmNotes} disabled={loading}
          style={{ alignSelf: 'flex-start', padding: '10px 24px', fontSize: 14 }}>
          {loading ? '渲染中...' : '🔊 确认音符，渲染音频'}
        </button>
      </div>
    );
  }

  // Generating
  if (step === 'generating') return (
    <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>
      <div className="spinner" style={{ width: 32, height: 32, margin: '0 auto 16px' }} />
      <p style={{ fontSize: 16, color: 'var(--text-primary)' }}>正在渲染音频...</p>
      <p style={{ fontSize: 13, marginTop: 8 }}>
        🎤 人声：MiMo TTS 逐段合成（优先处理）
      </p>
      <p style={{ fontSize: 13 }}>
        🎵 乐器：合成引擎并行渲染
      </p>
      <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 12 }}>
        请等待所有音轨渲染完成，人声合成可能需要较长时间
      </p>
    </div>
  );

  // Fallback - show arrangement info bar
  return arrangement ? (
    <div style={{ padding: '12px 20px', background: 'var(--bg-input)', borderBottom: '1px solid #30363d', fontSize: 13, display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'center' }}>
      <span style={{ color: 'var(--info)', fontWeight: 600 }}>{arrangement.title || '未命名'}</span>
      <span style={{ color: 'var(--text-muted)' }}>{arrangement.bpm || '?'} BPM</span>
      <span style={{ color: 'var(--text-muted)' }}>{arrangement.key || '?'}</span>
      <span style={{ color: 'var(--text-muted)' }}>{arrangement.tracks?.length || 0} 音轨</span>
      <button className="btn btn-small" onClick={onReset} style={{ marginLeft: 'auto' }}>新建歌曲</button>
    </div>
  ) : null;
}


