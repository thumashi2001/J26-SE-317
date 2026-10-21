/**
 * Read-only lecturer view of one authorized student's active plan.
 * Live scope never reaches the database.
 */

import { getActivePath } from './pathService.js';
import {
  LIVE_LECTURER_SCOPE,
  assertAssigned,
  assignedStudentIds,
  describeLecturerScope,
} from './lecturerScope.js';

function planSummary(path) {
  return {
    studentId: path.studentId,
    pathId: path.pathId,
    status: path.status,
    revision: path.revision,
    updatedAt: path.updatedAt,
    strategy: path.strategy,
    nextActivitySource: path.nextActivitySource,
    multiActionProtocol: path.multiActionPolicy?.protocol || null,
    multiActionActivated: path.multiActionPolicy?.activated === true,
    scheduling:
      'Calendar packing is weakest_stored_mastery_v1 (heuristic). A se-path-multi-v2 pin is labelled only when that policy selected the next activity.',
    engagement: path.engagement || null,
    activities: (path.activities || []).map((activity) => ({
      activityId: activity.activityId,
      topic: activity.topic,
      kind: activity.kind,
      status: activity.status,
      completionKind: activity.completionKind,
      scheduledDate: activity.scheduledDate,
      nextActivity: activity.nextActivity === true,
      recommendationSource: activity.recommendationSource,
    })),
    quizAnswerKeys: 'not included',
  };
}

export function lecturerScopeView(scope = LIVE_LECTURER_SCOPE) {
  return describeLecturerScope(scope);
}

export function listLecturerStudents(lecturerId, scope = LIVE_LECTURER_SCOPE) {
  const ids = assignedStudentIds(lecturerId, scope);
  return {
    lecturerId,
    operational: false,
    source: describeLecturerScope(scope).source,
    students: ids.map((studentId) => ({ studentId })),
  };
}

export async function readLecturerStudentPlan(db, lecturerId, studentId, scope = LIVE_LECTURER_SCOPE) {
  assertAssigned(lecturerId, studentId, scope);
  try {
    const path = await getActivePath(db, studentId);
    return { operational: false, plan: planSummary(path) };
  } catch (err) {
    if (err.code === 'no_active_path' || err.status === 404) {
      return {
        operational: false,
        plan: null,
        code: 'no_active_path',
        reason: 'This student has no active C4 study plan.',
      };
    }
    throw err;
  }
}
