import React, { useState, useRef } from 'react';
import { Upload, FileCheck, AlertCircle, Loader2 } from 'lucide-react';

interface FileDropzoneProps {
  onFileSelect: (file: File) => void;
  isUploading?: boolean;
  uploadProgress?: number;
  acceptedTypes?: string;
  maxSizeMB?: number;
  detectedType?: string;
  detectedLang?: string;
  confidence?: number;
  label?: string;
  className?: string;
}

export const FileDropzone: React.FC<FileDropzoneProps> = ({
  onFileSelect,
  isUploading = false,
  uploadProgress = 0,
  acceptedTypes = '.pdf, .png, .jpg, .jpeg',
  maxSizeMB = 25,
  detectedType,
  detectedLang,
  confidence,
  label = 'Upload Official Certificate / Deed',
  className = '',
}) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFiles = (files: FileList | null) => {
    if (!files || files.length === 0) return;
    const file = files[0];

    // Check size
    if (file.size > maxSizeMB * 1024 * 1024) {
      setErrorMessage(`File exceeds the maximum allowed size of ${maxSizeMB}MB.`);
      return;
    }

    setErrorMessage(null);
    onFileSelect(file);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    handleFiles(e.dataTransfer.files);
  };

  return (
    <div className={`flex flex-col gap-2 ${className}`}>
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !isUploading && fileInputRef.current?.click()}
        onKeyDown={(e) => {
          if ((e.key === 'Enter' || e.key === ' ') && !isUploading) {
            e.preventDefault();
            fileInputRef.current?.click();
          }
        }}
        tabIndex={0}
        role="button"
        className={`relative flex flex-col items-center justify-center p-6 border-2 border-dashed rounded-lg transition-colors cursor-pointer text-center bg-surface ${
          isDragOver
            ? 'border-accent bg-amber-50/40'
            : isUploading
            ? 'border-stoneBorder bg-stone-50 cursor-wait'
            : 'border-stoneBorder hover:border-primary hover:bg-stone-50/60'
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept={acceptedTypes}
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
          disabled={isUploading}
        />

        {isUploading ? (
          <div className="flex flex-col items-center gap-2">
            <Loader2 className="w-8 h-8 text-primary animate-spin" />
            <span className="text-xs font-semibold text-stone-700">Uploading & extracting OCR text...</span>
            <div className="w-48 h-1.5 bg-stone-200 rounded-full overflow-hidden mt-1">
              <div
                className="h-full bg-accent transition-all duration-200"
                style={{ width: `${Math.max(15, uploadProgress)}%` }}
              />
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-1.5 text-stone-600">
            <div className="w-10 h-10 rounded-full bg-stone-100 flex items-center justify-center text-primary mb-1">
              <Upload className="w-5 h-5" />
            </div>
            <span className="text-xs font-semibold text-stone-800">{label}</span>
            <p className="text-[11px] text-stone-500">
              Drag & drop scan or PDF here, or <span className="text-primary font-semibold underline">browse</span>
            </p>
            <span className="text-[10px] text-stone-600">
              PDF, PNG, JPG up to {maxSizeMB}MB • Color or Grayscale
            </span>
          </div>
        )}
      </div>

      {errorMessage && (
        <div className="flex items-center gap-1.5 text-xs text-status-inconsistent-text bg-status-inconsistent-bg p-2 rounded border border-status-inconsistent-border">
          <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Detected Metadata strip after upload */}
      {(detectedType || detectedLang || confidence !== undefined) && (
        <div className="flex flex-wrap items-center gap-3 p-2 bg-stone-50 rounded border border-stoneBorder text-xs text-stone-700">
          <div className="flex items-center gap-1 font-semibold text-status-verified-text">
            <FileCheck className="w-4 h-4 text-status-verified" />
            <span>Ingested</span>
          </div>
          {detectedType && (
            <div className="font-mono text-stone-600">
              Type: <strong className="text-stone-900">{detectedType.replace(/_/g, ' ')}</strong>
            </div>
          )}
          {detectedLang && (
            <div className="font-mono text-stone-600">
              Language: <strong className="text-stone-900 uppercase">{detectedLang}</strong>
            </div>
          )}
          {confidence !== undefined && (
            <div className="font-mono text-stone-600">
              Confidence:{' '}
              <strong className="text-stone-900 tabular-nums">
                {Math.round(confidence * 100)}%
              </strong>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
