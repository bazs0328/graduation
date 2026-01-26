export const TYPE_LABELS = {
  single: '单选',
  judge: '判断',
  short: '简答',
};

export const DIFFICULTY_LABELS = {
  Easy: '易',
  Medium: '中',
  Hard: '难',
};

const EMPTY_ANSWER_TEXT = '未作答';
const EMPTY_EXPECTED_TEXT = '未提供';

function normalizeChoice(answer) {
  if (!answer) {
    return null;
  }
  if (typeof answer === 'string') {
    const trimmed = answer.trim().toUpperCase();
    return trimmed || null;
  }
  if (typeof answer === 'object' && answer.choice) {
    const trimmed = String(answer.choice).trim().toUpperCase();
    return trimmed || null;
  }
  return null;
}

function normalizeJudge(answer) {
  if (typeof answer === 'boolean') {
    return answer;
  }
  if (answer && typeof answer.value === 'boolean') {
    return answer.value;
  }
  return null;
}

function normalizeText(answer, keys = []) {
  if (typeof answer === 'string') {
    const trimmed = answer.trim();
    return trimmed || null;
  }
  if (answer && typeof answer === 'object') {
    for (const key of keys) {
      const candidate = answer[key];
      if (typeof candidate === 'string') {
        const trimmed = candidate.trim();
        if (trimmed) {
          return trimmed;
        }
      }
    }
  }
  return null;
}

function formatChoice(choice, options, fallbackText) {
  if (!choice) {
    return fallbackText;
  }
  const index = choice.charCodeAt(0) - 65;
  if (Number.isInteger(index) && options && options[index]) {
    return `${choice}. ${options[index]}`;
  }
  return choice;
}

export function formatUserAnswer(type, answer, options) {
  if (type === 'single') {
    const choice = normalizeChoice(answer);
    return formatChoice(choice, options, EMPTY_ANSWER_TEXT);
  }
  if (type === 'judge') {
    const value = normalizeJudge(answer);
    if (value === null) {
      return EMPTY_ANSWER_TEXT;
    }
    return value ? '正确' : '错误';
  }
  if (type === 'short') {
    const text = normalizeText(answer, ['text']);
    return text || EMPTY_ANSWER_TEXT;
  }
  if (answer == null) {
    return EMPTY_ANSWER_TEXT;
  }
  return typeof answer === 'string' ? answer : JSON.stringify(answer);
}

export function formatExpectedAnswer(type, answer, options) {
  if (type === 'single') {
    const choice = normalizeChoice(answer);
    return formatChoice(choice, options, EMPTY_EXPECTED_TEXT);
  }
  if (type === 'judge') {
    const value = normalizeJudge(answer);
    if (value === null) {
      return EMPTY_EXPECTED_TEXT;
    }
    return value ? '正确' : '错误';
  }
  if (type === 'short') {
    const text = normalizeText(answer, ['reference_answer', 'text']);
    return text || '暂无参考答案';
  }
  if (answer == null) {
    return EMPTY_EXPECTED_TEXT;
  }
  return typeof answer === 'string' ? answer : JSON.stringify(answer);
}

export function formatRecommendation(summary) {
  if (!summary || typeof summary !== 'object') {
    return '暂无推荐';
  }
  const value = summary.next_quiz_recommendation;
  if (value === 'easy_first') {
    return '下次建议优先简单题。';
  }
  return '暂无特殊推荐。';
}
