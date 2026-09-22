/**
 * Browser Notification API helpers.
 *
 * Requests permission lazily on first use and provides a simple
 * `showNotification` that falls back silently when not supported
 * or permission is denied.
 */

function detectSupport(): boolean {
  return typeof window !== "undefined" && "Notification" in window
}

async function requestNotificationPermission(): Promise<boolean> {
  if (!detectSupport()) {
    return false
  }

  if (Notification.permission === "granted") {
    return true
  }

  if (Notification.permission === "denied") {
    return false
  }

  const result = await Notification.requestPermission()
  return result === "granted"
}

type BrowserNotificationOptions = {
  title: string
  body?: string
  icon?: string
  tag?: string
  onClick?: () => void
}

export async function showBrowserNotification({
  title,
  body,
  icon = "/favicon.ico",
  tag,
  onClick,
}: BrowserNotificationOptions): Promise<boolean> {
  try {
    const granted = await requestNotificationPermission()
    if (!granted) return false

    const notification = new Notification(title, { body, icon, tag })

    if (onClick) {
      notification.onclick = () => {
        window.focus()
        onClick()
      }
    }

    return true
  } catch {
    return false
  }
}
