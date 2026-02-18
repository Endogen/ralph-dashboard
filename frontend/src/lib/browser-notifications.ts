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

export async function requestNotificationPermission(): Promise<boolean> {
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

export function getPermissionState(): NotificationPermission | "unsupported" {
  if (!detectSupport()) return "unsupported"
  return Notification.permission
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
  const granted = await requestNotificationPermission()
  if (!granted) return false

  try {
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
