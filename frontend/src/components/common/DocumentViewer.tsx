import React, { useState } from 'react';
import { ZoomIn, ZoomOut, RotateCw, RefreshCw, Layers, ShieldAlert, Image as ImageIcon } from 'lucide-react';
import { api } from '../../services/api';
import { DocumentForensics } from '../../types';

interface DocumentViewerProps {
  documentId?: number;
  filePath?: string;
  docType?: string;
  forensics?: DocumentForensics;
  highlightRegion?: { x: number; y: number; w: number; h: number } | null;
  className?: string;
}

export const DocumentViewer: React.FC<DocumentViewerProps> = ({
  documentId,
  filePath,
  docType,
  forensics,
  highlightRegion,
  className = '',
}) => {
  const [zoom, setZoom] = useState(1);
  const [rotation, setRotation] = useState(0);
  const [activeOverlay, setActiveOverlay] = useState<'original' | 'heatmap' | 'annotated'>('original');

  const baseFileUrl = documentId ? api.getDocumentFileUrl(documentId) : '';
  const heatmapUrl = forensics?.heatmap_image_path ? api.getForensicsImageUrl(forensics.heatmap_image_path) : '';
  const annotatedUrl = forensics?.annotated_image_path ? api.getForensicsImageUrl(forensics.annotated_image_path) : '';

  const handleZoomIn = () => setZoom((prev) => Math.min(prev + 0.25, 3));
  const handleZoomOut = () => setZoom((prev) => Math.max(prev - 0.25, 0.5));
  const handleRotate = () => setRotation((prev) => (prev + 90) % 360);
  const handleReset = () => {
    setZoom(1);
    setRotation(0);
    setActiveOverlay('original');
  };

  // Determine current image src based on active overlay
  let currentImgSrc = baseFileUrl;
  if (activeOverlay === 'heatmap' && heatmapUrl) {
    currentImgSrc = heatmapUrl;
  } else if (activeOverlay === 'annotated' && annotatedUrl) {
    currentImgSrc = annotatedUrl;
  }

  return (
    <div className={`flex flex-col rounded-lg border border-stoneBorder bg-surface overflow-hidden shadow-sm ${className}`}>
      {/* Viewer Toolbar */}
      <div className="flex flex-wrap items-center justify-between p-2.5 border-b border-stoneBorder bg-stone-50 gap-2">
        {/* Overlay Switches */}
        <div className="flex items-center gap-1 bg-surface p-1 rounded border border-stoneBorder">
          <button
            onClick={() => setActiveOverlay('original')}
            className={`px-2.5 py-1 text-xs font-semibold rounded transition-colors ${
              activeOverlay === 'original'
                ? 'bg-primary text-white'
                : 'text-stone-700 hover:bg-stone-100'
            }`}
          >
            Original
          </button>
          <button
            onClick={() => setActiveOverlay('heatmap')}
            disabled={!heatmapUrl}
            className={`px-2.5 py-1 text-xs font-semibold rounded transition-colors ${
              activeOverlay === 'heatmap'
                ? 'bg-primary text-white'
                : heatmapUrl
                ? 'text-stone-700 hover:bg-stone-100'
                : 'text-stone-300 cursor-not-allowed'
            }`}
            title={!heatmapUrl ? 'Heatmap not generated for this file' : 'Error Level Analysis (ELA) Heatmap'}
          >
            ELA Heatmap
          </button>
          <button
            onClick={() => setActiveOverlay('annotated')}
            disabled={!annotatedUrl}
            className={`px-2.5 py-1 text-xs font-semibold rounded transition-colors ${
              activeOverlay === 'annotated'
                ? 'bg-primary text-white'
                : annotatedUrl
                ? 'text-stone-700 hover:bg-stone-100'
                : 'text-stone-300 cursor-not-allowed'
            }`}
            title={!annotatedUrl ? 'Forensic annotation not available' : 'Annotated Tampered Regions'}
          >
            Forensic Markings
          </button>
        </div>

        {/* Zoom & Rotation Controls */}
        <div className="flex items-center gap-1">
          <button
            onClick={handleZoomOut}
            className="p-1.5 rounded hover:bg-stone-200 text-stone-700 transition-colors focus-visible:ring-1"
            aria-label="Zoom out"
            title="Zoom out"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <span className="font-mono text-xs text-stone-600 px-1 tabular-nums">
            {Math.round(zoom * 100)}%
          </span>
          <button
            onClick={handleZoomIn}
            className="p-1.5 rounded hover:bg-stone-200 text-stone-700 transition-colors focus-visible:ring-1"
            aria-label="Zoom in"
            title="Zoom in"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            onClick={handleRotate}
            className="p-1.5 rounded hover:bg-stone-200 text-stone-700 transition-colors focus-visible:ring-1 ml-1"
            aria-label="Rotate 90 degrees clockwise"
            title="Rotate 90°"
          >
            <RotateCw className="w-4 h-4" />
          </button>
          <button
            onClick={handleReset}
            className="p-1.5 rounded hover:bg-stone-200 text-stone-700 transition-colors focus-visible:ring-1"
            aria-label="Reset zoom and rotation"
            title="Reset"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Main Document Canvas Viewport */}
      <div className="relative flex-1 min-h-[460px] bg-[#EAE8E1] overflow-auto flex items-center justify-center p-4">
        {currentImgSrc ? (
          <div
            className="relative transition-transform duration-150 ease-out origin-center shadow-lg bg-white rounded"
            style={{
              transform: `scale(${zoom}) rotate(${rotation}deg)`,
            }}
          >
            <img
              src={currentImgSrc}
              alt={docType ? `${docType.replace(/_/g, ' ')} view` : 'Document preview'}
              className="max-h-[620px] max-w-full object-contain select-none block"
              onError={(e) => {
                // If direct image fails (e.g. PDF without image renderer), show graceful spec notice
                const target = e.target as HTMLImageElement;
                target.style.display = 'none';
                if (target.nextElementSibling) {
                  (target.nextElementSibling as HTMLElement).style.display = 'flex';
                }
              }}
            />

            {/* Region highlight box if highlighted */}
            {highlightRegion && (
              <div
                className="absolute border-2 border-status-tampering bg-status-tampering/20 animate-pulse pointer-events-none"
                style={{
                  left: `${highlightRegion.x}px`,
                  top: `${highlightRegion.y}px`,
                  width: `${highlightRegion.w}px`,
                  height: `${highlightRegion.h}px`,
                }}
              />
            )}

            {/* Fallback for raw PDFs or missing binary */}
            <div
              style={{ display: 'none' }}
              className="w-[480px] h-[600px] flex-col items-center justify-center p-8 text-center bg-surface border border-stoneBorder"
            >
              <ImageIcon className="w-12 h-12 text-stone-400 mb-3" />
              <h4 className="font-semibold text-primary mb-1">Official Document File Loaded</h4>
              <p className="text-xs text-stone-500 mb-4 max-w-xs">
                {filePath || 'Uploaded certificate PDF / scan file'}
              </p>
              <a
                href={baseFileUrl}
                target="_blank"
                rel="noreferrer"
                className="px-3 py-1.5 bg-primary text-white rounded text-xs font-semibold hover:bg-primary-hover"
              >
                Open in Full Window
              </a>
            </div>
          </div>
        ) : (
          <div className="text-center p-8 text-stone-500">
            <ImageIcon className="w-12 h-12 mx-auto mb-2 opacity-50" />
            <p className="text-sm font-semibold">No document loaded</p>
            <p className="text-xs">Select a document from the left list to inspect</p>
          </div>
        )}
      </div>

      {/* Mandatory Disclaimer and Legend Footer */}
      <div className="p-2.5 bg-stone-50 border-t border-stoneBorder flex flex-wrap items-center justify-between text-xs text-stone-600 gap-2">
        <div className="flex items-center gap-1.5 font-medium text-stone-700">
          <ShieldAlert className="w-4 h-4 text-accent flex-shrink-0" />
          <span>Forensic signals are probabilities, not proof. Scrutiny officers always make the verdict.</span>
        </div>

        {/* Legend */}
        {activeOverlay !== 'original' && (
          <div className="flex items-center gap-3 text-[11px] font-mono">
            <span className="flex items-center gap-1">
              <span className="w-2.5 h-2.5 rounded-sm bg-yellow-400 inline-block border border-stone-400" /> ELA Differential
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2.5 h-2.5 rounded-sm bg-red-600 inline-block border border-stone-400" /> Splice Anomaly
            </span>
          </div>
        )}
      </div>
    </div>
  );
};
