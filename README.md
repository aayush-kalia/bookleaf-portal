# BookLeaf Author Support Portal

An AI-assisted support portal for BookLeaf Publishing. Authors log in, see their books and royalty position, and raise tickets. Admins work a prioritised queue where each ticket arrives already classified, scored for priority, and paired with a draft reply grounded in BookLeaf policy and the author's actual data.

| | |
|---|---|
| **Frontend** | https://bookleaf-portal-rust-delta.vercel.app |
| **Backend API** | https://bookleaf-portal-kuj1.onrender.com |
| **API docs (Swagger)** | https://bookleaf-portal-kuj1.onrender.com/docs |
| **Health check** | https://bookleaf-portal-kuj1.onrender.com/health |

> The backend runs on a free tier and sleeps when idle. The first request after a quiet period can take 30–60 seconds; open the health check first to wake it.

## Repository access

The source code is in a private GitHub repository. I did not have an email address to add as a collaborator when submitting, so I will add the evaluator as soon as one is provided.

## Demo accounts

Seeded with the assignment's sample dataset, unchanged (10 authors, 18 books, 3 admins). All authors share one password and all admins share another.

| Role | Name | Email | Password |
|---|---|---|---|
| Author | Priya Sharma | `priya.sharma@email.com` | `Author@123` |
| Author | Rohit Kapoor | `rohit.kapoor@email.com` | `Author@123` |
| Author | Ananya Reddy | `ananya.reddy@email.com` | `Author@123` |
| Author | Vikram Joshi | `vikram.joshi@email.com` | `Author@123` |
| Author | Meera Nair | `meera.nair@email.com` | `Author@123` |
| Author | Arjun Malhotra | `arjun.malhotra@email.com` | `Author@123` |
| Author | Sneha Kulkarni | `sneha.kulkarni@email.com` | `Author@123` |
| Author | Farhan Sheikh | `farhan.sheikh@email.com` | `Author@123` |
| Author | Kavita Deshmukh | `kavita.deshmukh@email.com` | `Author@123` |
| Author | Diya Chatterjee | `diya.chatterjee@email.com` | `Author@123` |
| Admin | Admin 1 | `admin1@bookleaf.test` | `Admin@123` |
| Admin | Admin 2 | `admin2@bookleaf.test` | `Admin@123` |
| Admin | Admin 3 | `admin3@bookleaf.test` | `Admin@123` |

## Features

**Author portal**

- Email/password login; each author sees only their own data.
- **My Books:** title, ISBN, genre, publication date, status, MRP, copies sold, royalty earned / paid / pending, with a royalty summary. Books still in production show a stage tracker instead of sales and royalty figures.
- **Submit a query:** book dropdown (or "General / Account level"), subject, description.
- **My Tickets:** status, original query, and admin replies, updating live without a page refresh.

**Admin portal**

- **Ticket queue:** filter by status, category, priority, date and assignee. Default sort is priority, then oldest first. Critical tickets and anything unresolved for over 48 hours are marked.
- **AI classification and priority:** each ticket gets a category and a Critical / High / Medium / Low priority automatically. Admins can override both; the AI's original suggestion is kept for comparison.
- **AI-drafted reply:** opening a ticket shows an editable draft with *missing information* chips and an *escalation* banner. Nothing is sent until the admin sends it.
- **Ticket management:** change status, assign to self, add internal notes that authors can never see.

**Categories:** Royalty & Payments · ISBN & Metadata Issues · Printing & Quality · Distribution & Availability · Book Status & Production Updates · General Inquiry

## Architecture

```text
React + Vite + TypeScript  (Vercel)
        │  REST + httpOnly cookie        ▲  Server-Sent Events
        ▼                                │
FastAPI  (Render)
  ├── api/        thin routes, auth and role dependencies
  ├── services/   ticket, royalty, event-broker logic
  ├── ai/         provider, classifier, drafter, context builder,
  │               retrieval, fallback rules, versioned prompts
  ├── schemas/    Pydantic request/response models
  └── models/     SQLAlchemy models
        │
        └── PostgreSQL (Neon)
```

The browser talks only to FastAPI. FastAPI owns authentication, all database access, and every AI call.

| Decision | Why |
|---|---|
| **Modular monolith** (FastAPI) | One process serves REST, SSE and AI calls. Routes stay thin, business rules live in services, and all AI code sits in one package so it can be read as a unit. |
| **PostgreSQL** | The data is strongly relational (authors, books, tickets, messages). Money uses `NUMERIC`. Full-text search covers knowledge-base retrieval, so no vector database is needed. |
| **JWT in an httpOnly cookie + CSRF token** | The token can't be read by page scripts. State-changing requests must carry an `X-CSRF-Token` header. CORS allows only the frontend origin. |
| **Server-Sent Events** | Updates flow one way, server to browser. Events carry only a ticket ID; the browser refetches through the normal REST API, so no ticket data travels over the stream. |
| **`LLMProvider` interface** | Model calls sit behind one interface, so changing provider is a configuration change, not a rewrite. |
| **Internal notes in their own table** | They can never leak into an author's response or an AI prompt by accident. |

## AI integration

Two jobs run behind the `LLMProvider` interface. Neither can block the ticket flow.

### 1. Classification and priority (on ticket creation)

1. `POST /tickets` saves the ticket and returns `201` immediately; the author never waits on the AI.
2. A background task sends the subject, the description (capped at 2,000 characters) and one line of book context to the model.
3. One call returns the category, the priority and a short reason as schema-enforced JSON (temperature 0, small output cap, no extended "thinking").
4. The result is validated. An unknown category or malformed JSON counts as a failure and is never stored.
5. The suggestion is stored in `ai_category` / `ai_priority` and copied into the live `category` / `priority`. An admin override changes only the live values, so the override rate can be measured.
6. **If the AI fails or is rate-limited,** keyword rules assign a category and priority instead, and the queue shows a small icon marking it as rule-based. The queue is never unsorted.

The prompt defines priority by the problem, not the tone: money unpaid for many months or a live book with a wrong ISBN is Critical; a bio update is Low, however angrily it is written.

### 2. Reply drafting (when an admin opens a ticket)

**The model writes the wording; the application supplies the facts.** Royalty totals, the ₹1,000 threshold, the next payout date and overdue status are computed in SQL and Python and passed to the model as a short facts block, for example:

```text
Ticket is about: "Whispers of the Ganges" (BK001)
  Earned ₹11,970 | Paid ₹8,400 | Pending ₹3,570 | Last payout 15 Oct 2025
Account royalty: pending ₹3,570 across all books (above the ₹1,000 threshold)
  Next scheduled payout due by 14 Feb 2026 | Overdue: no
```

Which facts are included depends on the ticket's author, book and category (an ISBN ticket gets ISBN and listing details; a royalty ticket gets earnings). A General ticket lists every book in one line.

Each draft prompt contains:

- **Static system prompt:** BookLeaf's tone guidelines (acknowledge first, own mistakes, give specific numbers and timelines, end with a clear next step).
- **Policy:** the top two knowledge-base chunks, ranked with PostgreSQL full-text search, filtered by ticket category plus general policy.
- **Examples:** one or two of the brief's sample query/response pairs for the category.
- **Author facts:** the block above.
- **Conversation:** the original ticket and the last five public messages, each capped at 1,500 characters.

The model may use only numbers from the facts and policy. When it needs something it doesn't have (for example, whether bank details are linked), it lists that under `missing_info` instead of guessing. The response is JSON: `draft`, `missing_info`, `needs_escalation`, `escalation_reason`.

**Safety:** author text is wrapped in tags and treated as data, never instructions. Internal notes are never included in a prompt.

**If drafting fails,** the editor loads a short generic holding reply (no amounts, dates or book details) with a banner saying the AI draft was unavailable. The admin can edit or replace it before sending, and it is not recorded as an AI-assisted reply.

### Cost controls

- Classification and priority share one call, and each ticket is classified once.
- Drafts are generated only when an admin opens a ticket, then cached. Re-opening costs zero tokens; a new author message triggers regeneration.
- A per-ticket lock stops two admins opening the same ticket from triggering two calls.
- Context is bounded: two policy chunks, one or two examples, five messages of at most 1,500 characters.
- Output length is capped on both calls.
- Static instructions come first in every prompt so provider-side prompt caching can reuse them.
- Every call is logged in `ai_runs` (tokens, latency, status, prompt version), so real averages can be read from the database.

### Model choice

I use **Gemini 3.5 Flash-Lite** (`gemini-3.5-flash-lite`, set by `LLM_MODEL`). Google positions it as a low-latency, low-cost model for high-volume work, which suits short, structured tasks like classification and reply drafting where a larger model would add cost without much benefit. It supports schema-enforced JSON output, and latency is low enough for an admin waiting on a draft. Because of the provider interface, switching to `gpt-4o-mini` or Claude Haiku means adding one class.

**Privacy note:** free-tier Gemini may use prompts to improve Google's products. This demo contains only the sample dataset. A production deployment would use a paid tier with reviewed data-retention terms, since real author data is confidential.

## API reference

Base path `/api/v1`. All routes except login and health require authentication. Interactive docs with full schemas: [`/docs`](https://bookleaf-portal-kuj1.onrender.com/docs).

| Method | Endpoint | Access | Purpose |
|---|---|---|---|
| POST | `/auth/login` | Public | Authenticate; sets auth and CSRF cookies |
| POST | `/auth/logout` | Any user | Clear cookies |
| GET | `/auth/me` | Any user | Current user, role and author profile |
| GET | `/books` | Author, Admin | Author: own books and royalty summary. Admin: all |
| GET | `/books/{book_id}` | Owner, Admin | One book |
| GET | `/tickets` | Author, Admin | Author: own tickets. Admin filters: `status`, `category`, `priority`, `assigned`, `created_from`, `created_to`, `sort`, `page`, `page_size` |
| POST | `/tickets` | Author | Create a ticket (`201`; classification runs in the background) |
| GET | `/tickets/{ticket_id}` | Owner, Admin | Ticket and public thread (AI fields for admins only) |
| PATCH | `/tickets/{ticket_id}` | Admin | Update status, category, priority or assignee |
| POST | `/tickets/{ticket_id}/messages` | Owner, Admin | Add a public reply |
| GET | `/tickets/{ticket_id}/notes` | Admin | List internal notes |
| POST | `/tickets/{ticket_id}/notes` | Admin | Add an internal note |
| GET | `/tickets/{ticket_id}/draft` | Admin | Cached or newly generated AI draft |
| GET | `/events/stream` | Author, Admin | Server-Sent Events stream |
| GET | `/admins` | Admin | Admin list for the assignee dropdown |
| GET | `/health` | Public | Liveness check |

### Access control

- Every route requires authentication except `/auth/login` and `/health`.
- Role checks run in FastAPI dependencies: authors calling an admin-only route get `403`.
- Ownership checks run in the service layer: an author requesting another author's ticket or book gets `404`, not `403`, so IDs can't be probed.
- Wrong email and wrong password return the same `401` message.
- Internal notes and AI fields are returned to admins only.

### Status rules

Invalid transitions return `409`. Closed is final.

| From | To | Who |
|---|---|---|
| open | in_progress, resolved, closed | Admin |
| in_progress | resolved, closed | Admin |
| resolved | in_progress, closed | Admin |
| resolved | open | Automatic, when the author posts a message |
| closed | none | Closed tickets accept no messages |

### Errors

Every non-2xx response uses one shape:

```json
{"error": {"code": "TICKET_NOT_FOUND", "message": "Ticket not found.", "details": []}}
```

| Code | Meaning |
|---|---|
| 400 | Bad request |
| 401 | Not logged in |
| 403 | Wrong role, or CSRF mismatch |
| 404 | Not found, or not yours |
| 409 | Invalid status change, or message on a Closed ticket |
| 422 | Validation error, with field names in `details` |
| 503 | AI unavailable |

Unexpected errors return a logged `500` with a request ID, never a stack trace.

## Assumptions

- **Reference date is fixed at 15 January 2026** (`APP_REFERENCE_DATE=2026-01-15`) instead of the real current date. The sample data is a snapshot from late 2025: the most recent payout is 1 December 2025. BookLeaf's policy pays royalties within 45 days of quarter end, so against today's real date almost every author with a pending balance would look many months overdue, and the overdue flag and next-payout dates would be meaningless. At 15 January 2026 the Q4 2025 payout (due by 14 February 2026) has not yet fallen due, so the calculations are consistent with the data. Change the variable to test other dates.

## Local setup

**Prerequisites:** Python 3.11+, Node.js 18+, PostgreSQL (local or Neon), a Gemini API key.

```bash
git clone <PRIVATE_REPO_URL> && cd bookleaf-portal

# Backend
cd backend
python -m venv .venv && source .venv/bin/activate    # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env                                  # then fill in values (see below)
alembic upgrade head
python -m scripts.seed                                # loads the sample data and demo accounts
python -m scripts.load_kb                             # loads the knowledge base
uvicorn app.main:app --reload                         # http://localhost:8000/docs

# Frontend (new terminal)
cd frontend
npm install
echo "VITE_API_URL=http://localhost:8000/api/v1" > .env.local
npm run dev
```

The seed script is idempotent. Do not run it against a database whose data you need to keep.

**Tests:** `cd backend && pytest` covers login, ownership (author A gets `404` on author B's records), role checks (`403`), status-transition rules, and AI failure (ticket still created, rule-based classification applied).

### Environment variables

Secrets live only in backend environment variables, locally and on the host. `.env` is git-ignored and `.env.example` lists every name with no values.

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `JWT_SECRET` | JWT signing secret |
| `FRONTEND_ORIGIN` | Exact frontend origin allowed by CORS |
| `COOKIE_SECURE` / `COOKIE_SAMESITE` | `true` / `none` for the cross-domain HTTPS deployment |
| `GEMINI_API_KEY` | LLM key, server-side only |
| `LLM_MODEL` | Model identifier |
| `APP_REFERENCE_DATE` | Fixed date for repeatable royalty calculations |

The frontend reads one public (non-secret) variable, `VITE_API_URL`.

## Known limitations and next steps

- **Cross-site cookies.** The frontend (Vercel) and API (Render) are on different domains, so login relies on `SameSite=None; Secure` cookies. Browsers that block third-party cookies by default, such as Safari, may fail to log in. Proxying `/api/*` through Vercel would make the cookie first-party.
- **Single-instance events.** The SSE broker lives in one process. Scaling needs PostgreSQL `LISTEN/NOTIFY` or Redis pub/sub.
- **Overdue is an approximation.** The supplied data has no per-quarter sales, so overdue status is a heuristic, not an accounting result. A per-quarter royalty ledger would fix this.
- **Sessions.** No refresh tokens or session revocation.
- **Attachments.** File attachments are not implemented; the brief lists them as optional.
- **AI.** Retrieval is keyword-based full-text search, which is enough for eight policy chunks but would move to hybrid or vector search at scale. Production would add a paid model tier, continuous accuracy tracking, and alerts on AI failure rate, latency and override rate.
- **Operations.** No email notifications, SLA alerts or CI pipeline yet.
