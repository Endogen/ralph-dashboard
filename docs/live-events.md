# Frontend live events

The layout owns one WebSocket connection. `useWebSocket` validates incoming JSON with `parseSocketMessage` and publishes application events through `liveEvents`. Successful authentication publishes a local `reconnected` event through that same channel. Protocol replies and unsupported events are not forwarded to application subscribers.

`useLiveEvent` gives each mounted consumer one subscription and uses its latest committed handler. Cleanup removes the subscription on unmount, including React StrictMode's setup/cleanup cycle. A subscriber failure is reported without preventing other subscribers from receiving the event. Events are ephemeral; authoritative state and reconnect recovery remain in the existing stores and HTTP APIs.

- `AppLayout` owns shared project status patches, project-list refreshes and notifications.
- `ProjectPage` owns project-specific overview refreshes, unread-log state and log-viewer refresh signals. It does not patch shared status.
- Both project stores preserve references for unchanged patches.
- The log viewer continues to reconcile through its HTTP cursor so batched updates, reconnect gaps and rotation cannot duplicate or omit displayed log content.

Consumed status, log and notification payloads have discriminated types and runtime validation at the socket boundary. Refresh-only events retain explicitly unknown payload fields; reading those fields in a new consumer requires validation. Adding a new consumed event means extending the shared contract and parser, then testing its consumer. There is no DOM event name or separate callback channel to keep synchronized. This is a maintainability boundary, not a security boundary against scripts already executing in the application.

## Verification

The frontend suite covers the real layout, project page, stores and log viewer with a simulated WebSocket and HTTP server responses. It verifies one socket, one shared active-project patch per status event, project filtering, log reconciliation, notifications, reconnect refreshes, retired-socket rejection, malformed messages, subscription cleanup and latest-handler delivery. Existing refresh-outage tests remain in place. Build/type checking and bundle budgets validate the production artifact.
