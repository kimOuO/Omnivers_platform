'use client';

import { useState, useMemo } from 'react';
import type { UsdAsset, Building } from '@/types';

interface ObjectFormProps {
  type: 'building' | 'gnb' | 'ue';
  assets: UsdAsset[];
  onSubmit: (data: Partial<Building>) => Promise<void>;
  onCancel: () => void;
  isLoading?: boolean;
}

export function ObjectForm({
  type,
  assets,
  onSubmit,
  onCancel,
  isLoading = false,
}: ObjectFormProps) {
  const [formData, setFormData] = useState({
    name: '',
    preset_id: '',
    position_x: 0,
    position_y: 0,
    position_z: 0,
    size_x: 10,
    size_y: 10,
    size_z: 10,
    color_r: 0.75,
    color_g: 0.75,
    color_b: 0.75,
  });

  const filteredAssets = useMemo(
    () =>
      type === 'building'
        ? assets.filter((a) => a.object_type === 'building')
        : type === 'ue'
          ? assets.filter((a) => a.object_type === 'ue')
          : assets.filter((a) => a.object_type === 'obstacle'),
    [assets, type]
  );

  const selectedAsset = useMemo(
    () =>
      filteredAssets.find((a) => a.preset_id === formData.preset_id),
    [filteredAssets, formData.preset_id]
  );

  const handlePresetChange = (presetId: string) => {
    setFormData((prev) => ({ ...prev, preset_id: presetId }));

    const asset = filteredAssets.find((a) => a.preset_id === presetId);
    if (asset?.default_size) {
      setFormData((prev) => ({
        ...prev,
        size_x: asset.default_size![0],
        size_y: asset.default_size![1],
        size_z: asset.default_size![2],
      }));
    }
    if (asset?.default_color) {
      setFormData((prev) => ({
        ...prev,
        color_r: asset.default_color![0],
        color_g: asset.default_color![1],
        color_b: asset.default_color![2],
      }));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const data: Partial<Building> = {
      name: formData.name,
      position: [formData.position_x, formData.position_y, formData.position_z] as [
        number,
        number,
        number
      ],
      color: [formData.color_r, formData.color_g, formData.color_b] as [
        number,
        number,
        number
      ],
    };

    if (type === 'building') {
      data.size = [formData.size_x, formData.size_y, formData.size_z] as [
        number,
        number,
        number
      ];
      if (formData.preset_id) {
        (data as any).preset_id = formData.preset_id;
      }
    }

    await onSubmit(data);
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <h2>Add {type === 'building' ? 'Building' : type === 'gnb' ? 'gNB' : 'UE'}</h2>

        <form onSubmit={handleSubmit}>
          {/* Name */}
          <div className="form-group">
            <label htmlFor="name">Name *</label>
            <input
              id="name"
              type="text"
              value={formData.name}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, name: e.target.value }))
              }
              required
            />
          </div>

          {/* Preset (for building/ue) */}
          {(type === 'building' || type === 'ue') && (
            <div className="form-group">
              <label htmlFor="preset">Preset Type</label>
              <select
                id="preset"
                value={formData.preset_id}
                onChange={(e) => handlePresetChange(e.target.value)}
              >
                <option value="">-- None --</option>
                {filteredAssets.map((asset) => (
                  <option key={asset.preset_id} value={asset.preset_id}>
                    {asset.label}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Position */}
          <div className="form-row">
            <div className="form-group">
              <label htmlFor="pos_x">Position X</label>
              <input
                id="pos_x"
                type="number"
                step="0.1"
                value={formData.position_x}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    position_x: parseFloat(e.target.value),
                  }))
                }
              />
            </div>
            <div className="form-group">
              <label htmlFor="pos_y">Position Y</label>
              <input
                id="pos_y"
                type="number"
                step="0.1"
                value={formData.position_y}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    position_y: parseFloat(e.target.value),
                  }))
                }
              />
            </div>
            <div className="form-group">
              <label htmlFor="pos_z">Position Z</label>
              <input
                id="pos_z"
                type="number"
                step="0.1"
                value={formData.position_z}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    position_z: parseFloat(e.target.value),
                  }))
                }
              />
            </div>
          </div>

          {/* Size (for building only) */}
          {type === 'building' && (
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="size_x">Size X</label>
                <input
                  id="size_x"
                  type="number"
                  step="0.1"
                  value={formData.size_x}
                  onChange={(e) =>
                    setFormData((prev) => ({
                      ...prev,
                      size_x: parseFloat(e.target.value),
                    }))
                  }
                />
              </div>
              <div className="form-group">
                <label htmlFor="size_y">Size Y</label>
                <input
                  id="size_y"
                  type="number"
                  step="0.1"
                  value={formData.size_y}
                  onChange={(e) =>
                    setFormData((prev) => ({
                      ...prev,
                      size_y: parseFloat(e.target.value),
                    }))
                  }
                />
              </div>
              <div className="form-group">
                <label htmlFor="size_z">Size Z</label>
                <input
                  id="size_z"
                  type="number"
                  step="0.1"
                  value={formData.size_z}
                  onChange={(e) =>
                    setFormData((prev) => ({
                      ...prev,
                      size_z: parseFloat(e.target.value),
                    }))
                  }
                />
              </div>
            </div>
          )}

          {/* Color */}
          <div className="form-row">
            <div className="form-group">
              <label htmlFor="color_r">Color R (0-1)</label>
              <input
                id="color_r"
                type="number"
                min="0"
                max="1"
                step="0.01"
                value={formData.color_r}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    color_r: parseFloat(e.target.value),
                  }))
                }
              />
            </div>
            <div className="form-group">
              <label htmlFor="color_g">Color G (0-1)</label>
              <input
                id="color_g"
                type="number"
                min="0"
                max="1"
                step="0.01"
                value={formData.color_g}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    color_g: parseFloat(e.target.value),
                  }))
                }
              />
            </div>
            <div className="form-group">
              <label htmlFor="color_b">Color B (0-1)</label>
              <input
                id="color_b"
                type="number"
                min="0"
                max="1"
                step="0.01"
                value={formData.color_b}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    color_b: parseFloat(e.target.value),
                  }))
                }
              />
            </div>
          </div>

          {/* Buttons */}
          <div className="form-actions">
            <button type="submit" disabled={isLoading || !formData.name}>
              {isLoading ? 'Creating...' : 'Create'}
            </button>
            <button type="button" onClick={onCancel} disabled={isLoading}>
              Cancel
            </button>
          </div>
        </form>
      </div>

      <style jsx>{`
        .modal-overlay {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0, 0, 0, 0.5);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 1000;
        }

        .modal-content {
          background: white;
          border-radius: 8px;
          padding: 24px;
          max-width: 600px;
          max-height: 90vh;
          overflow-y: auto;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        }

        h2 {
          margin: 0 0 16px 0;
          font-size: 20px;
          font-weight: 600;
        }

        form {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .form-group {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        .form-group label {
          font-size: 14px;
          font-weight: 500;
          color: #333;
        }

        .form-group input,
        .form-group select {
          padding: 8px 12px;
          border: 1px solid #ddd;
          border-radius: 4px;
          font-size: 14px;
          font-family: inherit;
        }

        .form-group input:focus,
        .form-group select:focus {
          outline: none;
          border-color: #0066cc;
          box-shadow: 0 0 0 2px rgba(0, 102, 204, 0.1);
        }

        .form-row {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 12px;
        }

        .form-actions {
          display: flex;
          gap: 8px;
          justify-content: flex-end;
          margin-top: 16px;
        }

        button {
          padding: 8px 16px;
          border: 1px solid #ddd;
          border-radius: 4px;
          font-size: 14px;
          cursor: pointer;
          background: white;
          transition: all 0.2s;
        }

        button[type='submit'] {
          background: #0066cc;
          color: white;
          border-color: #0066cc;
        }

        button[type='submit']:hover:not(:disabled) {
          background: #0052a3;
        }

        button[type='button'] {
          background: #f5f5f5;
        }

        button[type='button']:hover:not(:disabled) {
          background: #e8e8e8;
        }

        button:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
      `}</style>
    </div>
  );
}
