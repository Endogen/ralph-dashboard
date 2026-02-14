STATUS: COMPLETE

# Implementation Plan

## Phase 1: Backend Setup
- [x] 1.1: Initialize backend project (FastAPI, SQLAlchemy, Alembic, pyproject.toml)
- [x] 1.2: Configure settings (env vars: DB, JWT secret, SMTP, uploads path)
- [x] 1.3: Set up SQLAlchemy models base and database session
- [x] 1.4: Implement password hashing and JWT utilities
- [x] 1.5: Add global exception handling and API response schemas

## Phase 2: Backend Auth
- [x] 2.1: Create User and EmailToken models with migrations
- [x] 2.2: Implement register endpoint with email verification token
- [x] 2.3: Implement verify email endpoint
- [x] 2.4: Implement login/logout/refresh endpoints
- [x] 2.5: Implement forgot/reset password endpoints
- [x] 2.6: Implement /auth/me and DELETE /auth/me (account deletion)
- [x] 2.7: Add auth tests (unit + integration)

## Phase 3: Backend Collections
- [x] 3.1: Create Collection model with migrations
- [x] 3.2: Implement collection CRUD endpoints
- [x] 3.3: Implement public collections endpoints (no auth)
- [x] 3.4: Add collection tests

## Phase 4: Backend Schema
- [x] 4.1: Create FieldDefinition model with migrations
- [x] 4.2: Implement field CRUD endpoints
- [x] 4.3: Implement field reorder endpoint
- [x] 4.4: Add schema tests

## Phase 5: Backend Items
- [x] 5.1: Create Item model with migrations
- [x] 5.2: Implement metadata validation service
- [x] 5.3: Implement item CRUD endpoints
- [x] 5.4: Implement item list with search/filter/sort/pagination
- [x] 5.5: Add item tests

## Phase 6: Backend Images
- [x] 6.1: Create ItemImage model with migrations
- [x] 6.2: Implement image processing service (resize, convert to JPG)
- [x] 6.3: Implement image upload endpoint
- [x] 6.4: Implement image list/delete/reorder endpoints
- [x] 6.5: Implement image serving endpoint
- [x] 6.6: Add image tests

## Phase 7: Frontend Setup
- [x] 7.1: Initialize Next.js app with Tailwind and shadcn/ui
- [x] 7.2: Set up API client with auth handling
- [x] 7.3: Build layout (header, sidebar, responsive shell)
- [x] 7.4: Implement auth context and route guards

## Phase 8: Frontend Auth
- [x] 8.1: Build login and register pages
- [x] 8.2: Build email verification page
- [x] 8.3: Build forgot/reset password pages
- [x] 8.4: Build user settings page

## Phase 9: Frontend Collections
- [x] 9.1: Build collections list page
- [x] 9.2: Build collection create/edit forms
- [x] 9.3: Build schema builder component
- [x] 9.4: Build public collections explorer

## Phase 10: Frontend Items
- [x] 10.1: Build items list with search/filter/sort
- [x] 10.2: Build dynamic item form (from schema)
- [x] 10.3: Build item detail page

## Phase 11: Frontend Images
- [x] 11.1: Build image uploader (drag-drop + camera capture)
- [x] 11.2: Build image gallery with reorder
- [x] 11.3: Build image delete flow

## Phase 12: Docker & Polish
- [x] 12.1: Create Dockerfile for backend
- [x] 12.2: Create Dockerfile for frontend
- [x] 12.3: Create docker-compose.yml
- [x] 12.4: Verify 80% backend test coverage
- [x] 12.5: Final E2E smoke test
