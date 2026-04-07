import { useEffect, useRef, useState, useCallback } from 'react'
import { Html5Qrcode, Html5QrcodeSupportedFormats } from 'html5-qrcode'
import { decodeBarcode } from '../../api/items.ts'

interface Props {
  onScan: (code: string) => void
  onClose: () => void
}

const FORMATS = [
  Html5QrcodeSupportedFormats.EAN_13,
  Html5QrcodeSupportedFormats.UPC_A,
  Html5QrcodeSupportedFormats.CODE_128,
]

const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent)
  || (navigator.maxTouchPoints > 1 && /Macintosh/i.test(navigator.userAgent))

export default function BarcodeScanner({ onScan, onClose }: Props) {
  const scannerRef = useRef<Html5Qrcode | null>(null)
  const stoppingRef = useRef(false)
  const [error, setError] = useState<string | null>(null)
  const [status, setStatus] = useState<string | null>(null)
  const [mirrored, setMirrored] = useState(!isMobile)
  const [snapping, setSnapping] = useState(false)

  const handleDecode = useCallback((decodedText: string) => {
    stoppingRef.current = true
    scannerRef.current?.stop().catch(() => {}).finally(() => onScan(decodedText))
  }, [onScan])

  const stopScanner = useCallback(async () => {
    if (stoppingRef.current || !scannerRef.current) return
    stoppingRef.current = true
    try { await scannerRef.current.stop() } catch { /* already stopped */ }
  }, [])

  useEffect(() => {
    stoppingRef.current = false
    const scanner = new Html5Qrcode('barcode-reader', { formatsToSupport: FORMATS, verbose: false })
    scannerRef.current = scanner

    scanner.start(
      { facingMode: isMobile ? 'environment' : 'user' },
      { fps: 5, qrbox: { width: 250, height: 150 } },
      (decodedText) => handleDecode(decodedText),
      undefined,
    ).catch((err) => {
      if (!stoppingRef.current) {
        setError(err?.message?.includes('Permission')
          ? 'Camera access denied. Please allow camera access or type the barcode manually.'
          : 'Could not start camera. Try typing the barcode manually.')
      }
    })

    return () => { stopScanner() }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Server-side snap decode (fallback for when auto-scan struggles)
  const handleSnap = useCallback(async () => {
    setStatus('Decoding...')
    setSnapping(true)

    const video = document.querySelector('#barcode-reader video') as HTMLVideoElement | null
    if (!video) { setStatus('No video'); setSnapping(false); return }

    const vw = video.videoWidth
    const vh = video.videoHeight
    if (!vw || !vh) { setStatus('Video not ready'); setSnapping(false); return }

    const canvas = document.createElement('canvas')
    canvas.width = vw
    canvas.height = vh
    canvas.getContext('2d')!.drawImage(video, 0, 0)

    canvas.toBlob(async (blob) => {
      if (!blob) { setStatus('Capture failed'); setSnapping(false); return }
      try {
        const file = new File([blob], 'scan.png', { type: 'image/png' })
        const result = await decodeBarcode(file)
        handleDecode(result.barcode)
      } catch {
        setStatus('No barcode found — move closer and try again')
        setSnapping(false)
      }
    }, 'image/png')
  }, [handleDecode])

  return (
    <div className="relative">
      {error ? (
        <div className="text-sm text-red-500 py-4">{error}</div>
      ) : (
        <div
          id="barcode-reader"
          className="rounded overflow-hidden"
          style={mirrored ? { '--mirror': 'scaleX(-1)' } as React.CSSProperties : undefined}
        />
      )}
      {status && <div className={`text-xs mt-1 ${status.includes('Decoding') ? 'text-accent' : 'text-red-500'}`}>{status}</div>}
      <div className="flex gap-2 mt-2">
        {!error && (
          <button
            onClick={handleSnap}
            disabled={snapping}
            className="px-4 py-1.5 bg-accent text-white rounded text-sm hover:bg-accent-hover disabled:opacity-50"
          >
            {snapping ? 'Decoding...' : 'Snap'}
          </button>
        )}
        <button
          onClick={onClose}
          className="px-3 py-1.5 border border-border rounded text-sm hover:bg-bg-hover"
        >
          Cancel
        </button>
        {!error && (
          <button
            onClick={() => setMirrored((m) => !m)}
            className="px-3 py-1.5 border border-border rounded text-sm hover:bg-bg-hover"
          >
            {mirrored ? 'Unmirror' : 'Mirror'}
          </button>
        )}
      </div>
      <style>{`
        #barcode-reader video {
          transform: var(--mirror, none);
        }
      `}</style>
    </div>
  )
}
