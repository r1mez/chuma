/** 学习规划 API 封装 */

import request from '@/utils/request'

export interface LearningPlanRecommendationItem {
  rank: number
  knowledge_point: string
  question_id: number
  question_difficulty: number
  question_type: string
  predicted_correct_probability: number
  current_mastery: number
  rrf_score: number
  source_ranks: Record<string, number>
  reason: string
}

/** 原版 DyGKT 预测 + 加权 RRF 决策层的下一步练习候选 */
export interface LearningPlanRecommendation {
  status: 'model' | 'cold_start_fallback' | 'heuristic_fallback' | 'no_candidates' | 'unavailable'
  model_version: string | null
  history_event_count: number
  candidate_count: number
  target_correct_probability?: number
  fusion?: {
    method: string
    rrf_k: number
    source_weights: Record<string, number>
    active_sources: string[]
  }
  recommendations: LearningPlanRecommendationItem[]
  message?: string
}

/** 单学科学习规划结果 */
export interface SubjectPlan {
  course_id: number
  course_name: string
  /** ok=已生成规划 / insufficient=维度不足 / db_error=数据库异常 */
  status: 'ok' | 'insufficient' | 'db_error'
  dimensions_available: number
  weights: {
    ai_analysis: number
    knowledge_mastery: number
    exercise: number
    teacher_opinion: number
  }
  dimensions_detail: Record<string, unknown>
  missing_dimensions: string[]
  error: string | null
  error_message?: string
  recommendation: LearningPlanRecommendation | null
  plan: {
    overall_goal: string
    weak_points: string[]
    weekly_plan: Array<{
      week: number
      theme: string
      tasks: string[]
      exercises: string
    }>
    priority_focus: string[]
    teacher_notes: string
  } | null
}

/** 学习规划整体结果 */
export interface LearningPlanResult {
  stu_id: number
  subjects: SubjectPlan[]
  error: string | null
  error_message?: string
}

/** 发起学习规划（按学科分别制定） */
export const fetchLearningPlan = (stuId: number): Promise<LearningPlanResult> => {
  return request.post<LearningPlanResult>(
    '/ai/analysis/learning_plan',
    { stu_id: stuId },
    { timeout: 300000 }, // 学习规划涉及多轮 LLM 调用（4 学科 × ReAct 循环），放宽超时
  )
}
