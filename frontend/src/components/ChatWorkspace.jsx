import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError } from '../services/http'
import { GENERIC_ERROR_MESSAGE, sendChatMessage } from '../services/api'
import { getDocuments, uploadDocument } from '../services/documents'
import { getWorkspaces } from '../services/workspaces'
import AdminPanel from './AdminPanel'
import ChatHeader from './ChatHeader'
import ChatInput from './ChatInput'
import ChatMessages from './ChatMessages'
import DocumentSidebar from './DocumentSidebar'
import Header from './Header'

// 4xx answers (except 401, handled by the auth hook) carry a message meant
// for the user, e.g. "At least one document_id is required." Anything else
// stays generic so server internals are never shown.
function chatErrorMessage(error) {
  if (
    error instanceof ApiError &&
    error.status >= 400 &&
    error.status < 500 &&
    error.status !== 401
  ) {
    return error.message
  }

  return GENERIC_ERROR_MESSAGE
}

function ChatWorkspace({ user, onLogout }) {
  const [messages, setMessages] = useState([])
  const [isThinking, setIsThinking] = useState(false)
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)

  const [workspaces, setWorkspaces] = useState([])
  const [workspacesLoaded, setWorkspacesLoaded] = useState(false)
  const [workspacesError, setWorkspacesError] = useState(null)
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState(null)

  const [documents, setDocuments] = useState([])
  const [documentsError, setDocumentsError] = useState(null)
  // null = ask across every document in the workspace
  const [selectedDocumentId, setSelectedDocumentId] = useState(null)

  const [isUploading, setIsUploading] = useState(false)
  const [uploadError, setUploadError] = useState(null)

  const [isAdminOpen, setIsAdminOpen] = useState(false)
  const closeAdmin = useCallback(() => setIsAdminOpen(false), [])

  // Always the workspace the user is looking at *now*, so a slow response for
  // a workspace they already left can be recognised and dropped.
  const selectedWorkspaceRef = useRef(null)

  const isAdmin = user.role === 'admin'

  async function loadWorkspaces() {
    try {
      const data = await getWorkspaces()

      const currentId = selectedWorkspaceRef.current
      const stillThere = data.some(
        (workspace) => workspace.workspace_id === currentId,
      )

      // The selected workspace was deleted (by an admin): start over.
      if (currentId && !stillThere) {
        setSelectedDocumentId(null)
        setDocuments([])
        setMessages([])
      }

      setWorkspaces(data)
      setWorkspacesError(null)
      setSelectedWorkspaceId(
        stillThere ? currentId : (data[0]?.workspace_id ?? null),
      )
    } catch (error) {
      console.error('Failed to load workspaces:', error)
      setWorkspacesError('Failed to load workspaces')
    } finally {
      setWorkspacesLoaded(true)
    }
  }

  async function loadDocuments(workspaceId) {
    try {
      const data = await getDocuments(workspaceId)

      // The user switched workspace while this request was running.
      if (selectedWorkspaceRef.current !== workspaceId) return false

      setDocuments(data)
      setDocumentsError(null)

      return true
    } catch (error) {
      console.error('Failed to load documents:', error)

      if (selectedWorkspaceRef.current !== workspaceId) return false

      setDocuments([])
      setDocumentsError('Failed to load documents')

      return false
    }
  }

  // Load the user's workspaces once on mount.
  useEffect(() => {
    loadWorkspaces()
  }, [])

  // Keep the ref in step with the selection (declared before the loader below
  // so it is already up to date when that effect runs).
  useEffect(() => {
    selectedWorkspaceRef.current = selectedWorkspaceId
  }, [selectedWorkspaceId])

  // Reload documents whenever the workspace changes.
  useEffect(() => {
    if (!selectedWorkspaceId) return

    loadDocuments(selectedWorkspaceId)
  }, [selectedWorkspaceId])

  function handleSelectWorkspace(workspaceId) {
    if (isThinking || workspaceId === selectedWorkspaceId) return

    // A conversation belongs to one workspace; start fresh in the new one.
    setSelectedWorkspaceId(workspaceId)
    setSelectedDocumentId(null)
    setDocuments([])
    setMessages([])
    setUploadError(null)
  }

  async function handleUpload(file) {
    if (isUploading || !selectedWorkspaceId) return

    setIsUploading(true)
    setUploadError(null)

    try {
      const uploadedDocument = await uploadDocument(file, selectedWorkspaceId)

      const reloadSucceeded = await loadDocuments(selectedWorkspaceId)

      if (reloadSucceeded) {
        setSelectedDocumentId(uploadedDocument.document_id)
      }

      // refresh the per-workspace document counts in the selector
      loadWorkspaces()
    } catch (error) {
      console.error('Document upload failed:', error)
      setUploadError(
        error instanceof ApiError && error.status >= 400 && error.status < 500
          ? error.message
          : 'Failed to upload document',
      )
    } finally {
      setIsUploading(false)
    }
  }

  const selectedWorkspace =
    workspaces.find(
      (workspace) => workspace.workspace_id === selectedWorkspaceId,
    ) ?? null

  const selectedDocument =
    documents.find(
      (document) => document.document_id === selectedDocumentId,
    ) ?? null

  async function handleSend(text) {
    if (isThinking || !selectedWorkspaceId) return

    const nextMessages = [
      ...messages,
      {
        id: crypto.randomUUID(),
        role: 'user',
        content: text,
      },
    ]

    setMessages(nextMessages)
    setIsThinking(true)

    try {
      const history = nextMessages
        .filter((message) => !message.error)
        .map(({ role, content }) => ({ role, content }))

      const response = await sendChatMessage({
        messages: history,
        documentIds: selectedDocumentId ? [selectedDocumentId] : [],
        workspaceId: selectedWorkspaceId,
      })

      setMessages((previous) => [
        ...previous,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: response.answer,
          sources: response.sources,
          traces: response.traces,
          answerId: response.answerId,
          confidence: response.confidence,
          confidenceLevel: response.confidenceLevel,
        },
      ])
    } catch (error) {
      console.error('Chat request failed:', error)

      setMessages((previous) => [
        ...previous,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: chatErrorMessage(error),
          error: true,
        },
      ])
    } finally {
      setIsThinking(false)
    }
  }

  function handleSelectDocument(documentId) {
    setSelectedDocumentId(documentId)
    setIsSidebarOpen(false)
  }

  const noWorkspaceAccess =
    workspacesLoaded && !workspacesError && workspaces.length === 0

  return (
    <div className="flex h-dvh flex-col bg-slate-50 text-slate-800 dark:bg-slate-950 dark:text-slate-100">
      <Header
        onToggleSidebar={() => setIsSidebarOpen((open) => !open)}
        user={user}
        onLogout={onLogout}
        onOpenAdmin={isAdmin ? () => setIsAdminOpen(true) : undefined}
      />

      {isAdminOpen && (
        <AdminPanel
          user={user}
          workspaces={workspaces}
          onClose={closeAdmin}
          onWorkspacesChanged={loadWorkspaces}
        />
      )}

      <div className="flex min-h-0 flex-1">
        {isSidebarOpen && (
          <button
            type="button"
            aria-label="Close document sidebar"
            onClick={() => setIsSidebarOpen(false)}
            className="fixed top-14 right-0 bottom-0 left-0 z-30 bg-slate-900/40 dark:bg-black/60 md:hidden"
          />
        )}

        <DocumentSidebar
          workspaces={workspaces}
          selectedWorkspaceId={selectedWorkspaceId}
          onSelectWorkspace={handleSelectWorkspace}
          workspaceSelectDisabled={isThinking}
          canUpload={isAdmin && Boolean(selectedWorkspaceId)}
          documents={documents}
          documentsError={workspacesError ?? documentsError}
          selectedDocumentId={selectedDocumentId}
          isOpen={isSidebarOpen}
          onSelect={handleSelectDocument}
          onClose={() => setIsSidebarOpen(false)}
          onUpload={handleUpload}
          isUploading={isUploading}
          uploadError={uploadError}
        />

        <main className="flex min-w-0 flex-1 flex-col bg-white dark:border-slate-700 dark:bg-slate-900 md:border-l md:border-slate-200">
          {noWorkspaceAccess ? (
            <section className="flex flex-1 items-center justify-center px-6 py-10">
              <div className="max-w-sm text-center">
                <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-50">
                  No workspace access yet
                </h2>
                <p className="mt-2 text-sm leading-6 text-slate-500 dark:text-slate-400">
                  Your account is not assigned to any workspace. Ask an
                  administrator to give you access.
                </p>
              </div>
            </section>
          ) : (
            <>
              <ChatHeader
                workspaceName={selectedWorkspace?.name}
                selectedDocument={selectedDocument}
                documentCount={documents.length}
                isThinking={isThinking}
              />

              <ChatMessages
                messages={messages}
                isThinking={isThinking}
              />

              <ChatInput
                onSend={handleSend}
                disabled={
                  isThinking || !selectedWorkspaceId || documents.length === 0
                }
                placeholder={
                  selectedWorkspaceId && documents.length === 0
                    ? 'This workspace has no documents yet'
                    : 'Ask about your documents...'
                }
              />
            </>
          )}
        </main>
      </div>
    </div>
  )
}

export default ChatWorkspace
