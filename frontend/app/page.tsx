'use client';

import { useState } from 'react';
import { useSceneEditor } from '@/hooks/feature/useSceneEditor';
import { ObjectForm } from '@/components/ObjectForm';

export default function ScenePage() {
  const editor = useSceneEditor();
  const [showForm, setShowForm] = useState(false);
  const [formType, setFormType] = useState<'building' | 'gnb' | 'ue'>('building');
  const [sceneId, setSceneId] = useState('default_scene');

  const handleOpenForm = (type: 'building' | 'gnb' | 'ue') => {
    setFormType(type);
    setShowForm(true);
  };

  const handleCloseForm = () => {
    setShowForm(false);
  };

  const handleFormSubmit = async (data: any) => {
    try {
      await editor.createBuilding(data);
      setShowForm(false);
    } catch (err) {
      console.error('Failed to create building', err);
    }
  };

  const loading =
    editor.buildings.status === 'loading' ||
    editor.gnbs.status === 'loading' ||
    editor.ues.status === 'loading' ||
    editor.assets.status === 'loading';

  const error =
    editor.buildings.error?.message ||
    editor.gnbs.error?.message ||
    editor.ues.error?.message ||
    editor.assets.error?.message;

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '24px' }}>
      <h1>Scene Editor</h1>

      {error && (
        <div style={{ color: '#d32f2f', padding: '12px', marginBottom: '16px' }}>
          {error}
        </div>
      )}

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
          gap: '24px',
          marginBottom: '24px',
        }}
      >
        {/* Buildings Section */}
        <div
          style={{
            border: '1px solid #ddd',
            borderRadius: '8px',
            padding: '16px',
          }}
        >
          <h2>Buildings ({editor.buildings.data?.length || 0})</h2>
          {editor.buildings.data?.length ? (
            <ul style={{ margin: '12px 0', paddingLeft: '20px' }}>
              {editor.buildings.data.map((b) => (
                <li key={b.name} style={{ marginBottom: '8px' }}>
                  <span>{b.name}</span>
                  <button
                    style={{
                      marginLeft: '12px',
                      padding: '4px 8px',
                      fontSize: '12px',
                      background: '#f5f5f5',
                      border: '1px solid #ddd',
                      borderRadius: '4px',
                      cursor: 'pointer',
                    }}
                    onClick={() => editor.deleteBuilding(b.name)}
                    disabled={editor.isDeleting}
                  >
                    Delete
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p style={{ color: '#999', margin: '12px 0' }}>No buildings</p>
          )}
          <button
            style={{
              marginTop: '12px',
              padding: '8px 12px',
              background: '#0066cc',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
            onClick={() => handleOpenForm('building')}
            disabled={editor.isCreating || editor.assets.status === 'loading'}
          >
            + Add Building
          </button>
        </div>

        {/* gNBs Section */}
        <div
          style={{
            border: '1px solid #ddd',
            borderRadius: '8px',
            padding: '16px',
          }}
        >
          <h2>gNBs ({editor.gnbs.data?.length || 0})</h2>
          {editor.gnbs.data?.length ? (
            <ul style={{ margin: '12px 0', paddingLeft: '20px' }}>
              {editor.gnbs.data.map((g) => (
                <li key={g.name} style={{ marginBottom: '4px' }}>
                  {g.name} ({g.frequency_ghz} GHz)
                </li>
              ))}
            </ul>
          ) : (
            <p style={{ color: '#999', margin: '12px 0' }}>No gNBs</p>
          )}
        </div>

        {/* UEs Section */}
        <div
          style={{
            border: '1px solid #ddd',
            borderRadius: '8px',
            padding: '16px',
          }}
        >
          <h2>UEs ({editor.ues.data?.length || 0})</h2>
          {editor.ues.data?.length ? (
            <ul style={{ margin: '12px 0', paddingLeft: '20px' }}>
              {editor.ues.data.map((u) => (
                <li key={u.name} style={{ marginBottom: '4px' }}>
                  {u.name}
                </li>
              ))}
            </ul>
          ) : (
            <p style={{ color: '#999', margin: '12px 0' }}>No UEs</p>
          )}
        </div>
      </div>

      {/* Apply Scene Section */}
      <div style={{ marginTop: '32px' }}>
        <h2>Apply to Simulation</h2>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-end' }}>
          <div>
            <label htmlFor="scene-id">Scene ID:</label>
            <input
              id="scene-id"
              type="text"
              value={sceneId}
              onChange={(e) => setSceneId(e.target.value)}
              style={{
                marginTop: '4px',
                padding: '8px 12px',
                border: '1px solid #ddd',
                borderRadius: '4px',
              }}
            />
          </div>
          <button
            style={{
              padding: '8px 16px',
              background: '#00aa33',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
            onClick={() => editor.applyScene(sceneId)}
            disabled={editor.isApplying || loading}
          >
            {editor.isApplying ? 'Applying...' : 'Apply Scene'}
          </button>
        </div>
      </div>

      {/* Form Modal */}
      {showForm && (
        <ObjectForm
          type={formType}
          assets={editor.assets.data || []}
          onSubmit={handleFormSubmit}
          onCancel={handleCloseForm}
          isLoading={editor.isCreating}
        />
      )}
    </div>
  );
}
