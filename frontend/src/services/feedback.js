import { apiFetch } from './http'

// rating: 'up' | 'down'. Sending again for the same answer replaces the
// earlier rating, so the comment is resent along with it.
export function submitFeedback(answerId, rating, comment = '') {
  return apiFetch('/feedback', {
    method: 'POST',
    json: { answer_id: answerId, rating, comment },
  })
}
