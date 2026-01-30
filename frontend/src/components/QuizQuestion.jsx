import { DIFFICULTY_LABELS, TYPE_LABELS } from '../lib/quizFormat';

function letterForIndex(index) {
  return String.fromCharCode(65 + index);
}

export default function QuizQuestion({ question, index, value, onChange }) {
  if (!question) {
    return null;
  }

  return (
    <div className="question">
      <div className="question-meta">
        <span className="badge">{TYPE_LABELS[question.type] || question.type}</span>
        <span className="badge">
          {DIFFICULTY_LABELS[question.difficulty] || question.difficulty}
        </span>
      </div>
      <p className="question-title">
        {index + 1}. {question.stem}
      </p>
      {question.options?.length ? (
        <div className="options">
          {question.options.map((option, optionIndex) => {
            const letter = letterForIndex(optionIndex);
            return (
              <label className="option" key={letter}>
                <input
                  type="radio"
                  name={`q-${question.question_id}`}
                  value={letter}
                  checked={value === letter}
                  onChange={() => onChange(question.question_id, letter)}
                />
                <span>
                  {letter}. {option}
                </span>
              </label>
            );
          })}
        </div>
      ) : null}
      {question.type === 'judge' && (
        <div className="options">
          <label className="option">
            <input
              type="radio"
              name={`q-${question.question_id}`}
              checked={value === true}
              onChange={() => onChange(question.question_id, true)}
            />
            <span>正确</span>
          </label>
          <label className="option">
            <input
              type="radio"
              name={`q-${question.question_id}`}
              checked={value === false}
              onChange={() => onChange(question.question_id, false)}
            />
            <span>错误</span>
          </label>
        </div>
      )}
      {(question.type === 'short'
        || question.type === 'fill_blank'
        || question.type === 'calculation'
        || question.type === 'written') && (
        <label className="field">
          <span>你的回答</span>
          <textarea
            className="input"
            rows="3"
            value={value || ''}
            onChange={(event) => onChange(question.question_id, event.target.value)}
          />
        </label>
      )}
      {question.explanation && <p className="subtle">解析：{question.explanation}</p>}
    </div>
  );
}
