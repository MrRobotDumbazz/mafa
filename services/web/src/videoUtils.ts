export async function getVideoDuration(file: File): Promise<number> {
  const url = URL.createObjectURL(file)
  return new Promise((resolve, reject) => {
    const video = document.createElement('video')
    video.preload = 'metadata'
    video.onloadedmetadata = () => {
      URL.revokeObjectURL(url)
      resolve(isFinite(video.duration) && video.duration > 0 ? video.duration : 60)
    }
    video.onerror = () => {
      URL.revokeObjectURL(url)
      reject(new Error('Не удалось прочитать метаданные видео'))
    }
    video.src = url
  })
}

export async function extractFramesFromFile(
  file: File,
  timesSec: number[],
): Promise<string[]> {
  const url = URL.createObjectURL(file)
  try {
    return await extractFromUrl(url, timesSec)
  } catch {
    return timesSec.map((_, i) => makeFallbackFrame(`Кадр ${i + 1}`))
  } finally {
    URL.revokeObjectURL(url)
  }
}

async function extractFromUrl(url: string, timesSec: number[]): Promise<string[]> {
  const video = document.createElement('video')
  video.muted = true
  video.preload = 'auto'
  video.src = url

  await new Promise<void>((resolve, reject) => {
    const tid = setTimeout(() => reject(new Error('Video load timeout')), 15_000)
    video.addEventListener(
      'canplay',
      () => {
        clearTimeout(tid)
        resolve()
      },
      { once: true },
    )
    video.addEventListener(
      'error',
      () => {
        clearTimeout(tid)
        reject(new Error('Video decode error'))
      },
      { once: true },
    )
    video.load()
  })

  const frames: string[] = []
  for (const t of timesSec) {
    const clamped = Math.max(0, Math.min(t, video.duration - 0.05))
    frames.push(await seekAndCapture(video, clamped))
  }
  return frames
}

function seekAndCapture(video: HTMLVideoElement, timeSec: number): Promise<string> {
  return new Promise((resolve, reject) => {
    const tid = setTimeout(() => reject(new Error('Seek timeout')), 8_000)
    video.addEventListener(
      'seeked',
      () => {
        clearTimeout(tid)
        const w = video.videoWidth || 320
        const h = video.videoHeight || 180
        const canvas = document.createElement('canvas')
        canvas.width = w
        canvas.height = h
        canvas.getContext('2d')!.drawImage(video, 0, 0, w, h)
        resolve(canvas.toDataURL('image/jpeg', 0.82).replace('data:image/jpeg;base64,', ''))
      },
      { once: true },
    )
    video.addEventListener('error', () => { clearTimeout(tid); reject(new Error('Seek error')) }, { once: true })
    video.currentTime = timeSec
  })
}

function makeFallbackFrame(label: string): string {
  const canvas = document.createElement('canvas')
  canvas.width = 320
  canvas.height = 180
  const ctx = canvas.getContext('2d')!
  ctx.fillStyle = '#374151'
  ctx.fillRect(0, 0, 320, 180)
  ctx.fillStyle = '#9ca3af'
  ctx.font = '13px sans-serif'
  ctx.textAlign = 'center'
  ctx.fillText(label, 160, 95)
  return canvas.toDataURL('image/jpeg', 0.7).replace('data:image/jpeg;base64,', '')
}
