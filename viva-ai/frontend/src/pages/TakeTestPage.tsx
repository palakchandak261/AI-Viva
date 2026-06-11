import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { Clock, AlertCircle, CheckCircle, Send } from 'lucide-react'
import api from '../../services/api'

export default function TakeTestPage() {
  const { classroomId, testId } = useParams()
  const navigate = useNavigate()
  const [test, setTest] = useState(null)
  const [loading, setLoading] = useState(true)
  const [testStarted, setTestStarted] = useState(false)
  const [timeRemaining, setTimeRemaining] = useState(null)
  const [marks, setMarks] = useState('')
  const [notes, setNotes] = useState('')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    fetchTest()
  }, [classroomId, testId])

  const fetchTest = async () => {
    try {
      setLoading(true)
      const response = await api.get(`/api/classrooms/${classroomId}/tests/${testId}`)
      setTest(response.data)
      setError(null)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to load test')
      setTimeout(() => navigate(`/classroom/${classroomId}`), 2000)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!testStarted || !test) return

    const duration = test.duration_minutes * 60 // Convert to seconds
    setTimeRemaining(duration)

    const timer = setInterval(() => {
      setTimeRemaining(prev => {
        if (prev <= 1) {
          clearInterval(timer)
          handleAutoSubmit()
          return 0
        }
        return prev - 1
      })
    }, 1000)

    return () => clearInterval(timer)
  }, [testStarted, test])

  const formatTime = (seconds) => {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    const secs = seconds % 60

    if (hours > 0) {
      return `${hours}h ${minutes}m ${secs}s`
    }
    return `${minutes}m ${secs}s`
  }

  const handleStartTest = () => {
    setTestStarted(true)
    toast.success('Test started! Good luck! 🍀')
  }

  const handleSubmitTest = async (e) => {
    e.preventDefault()

    if (!marks) {
      toast.error('Please enter your marks')
      return
    }

    const obtainedMarks = parseFloat(marks)
    if (obtainedMarks < 0 || obtainedMarks > test.total_marks) {
      toast.error(`Marks should be between 0 and ${test.total_marks}`)
      return
    }

    try {
      setSubmitting(true)
      const response = await api.post(
        `/api/classrooms/${classroomId}/tests/${testId}/results`,
        {
          test_id: testId,
          obtained_marks: obtainedMarks,
          notes: notes || null
        }
      )

      toast.success('Test submitted successfully!')
      navigate(`/classroom/${classroomId}/test-result/${response.data.id}`)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to submit test')
    } finally {
      setSubmitting(false)
    }
  }

  const handleAutoSubmit = async () => {
    toast.error('Time is up! Submitting your test...')
    // Auto submit with current marks
    try {
      await api.post(
        `/api/classrooms/${classroomId}/tests/${testId}/results`,
        {
          test_id: testId,
          obtained_marks: parseFloat(marks) || 0,
          notes: notes || null
        }
      )
      navigate(`/classroom/${classroomId}`)
    } catch (err) {
      console.error('Auto-submit error:', err)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    )
  }

  if (!test) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
        <p>Test not found</p>
      </div>
    )
  }

  if (!testStarted) {
    return <TestInstructions test={test} onStart={handleStartTest} />
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* Timer Header */}
      <div className={`sticky top-0 z-50 ${
        timeRemaining <= 600 ? 'bg-red-500' : 'bg-blue-600'
      } text-white rounded-lg p-4 mb-6 shadow-lg`}>
        <div className="flex justify-between items-center">
          <div>
            <h2 className="text-xl font-bold">{test.title}</h2>
            <p className="text-sm opacity-90">Total Marks: {test.total_marks}</p>
          </div>
          <div className="text-right">
            <div className="flex items-center gap-2 justify-end">
              <Clock size={24} />
              <div>
                <p className="text-sm opacity-90">Time Remaining</p>
                <p className="text-3xl font-mono font-bold">{formatTime(timeRemaining)}</p>
              </div>
            </div>
            {timeRemaining <= 600 && (
              <p className="text-xs mt-2 text-yellow-100">⚠️ Less than 10 minutes left!</p>
            )}
          </div>
        </div>
      </div>

      {/* Test Content */}
      <div className="bg-white rounded-lg shadow-lg p-8">
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Test Details</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-blue-50 p-3 rounded">
              <p className="text-xs text-gray-600 uppercase">Difficulty</p>
              <p className="font-semibold text-gray-900 capitalize">{test.difficulty_level}</p>
            </div>
            <div className="bg-green-50 p-3 rounded">
              <p className="text-xs text-gray-600 uppercase">Total Marks</p>
              <p className="font-semibold text-gray-900">{test.total_marks}</p>
            </div>
            <div className="bg-purple-50 p-3 rounded">
              <p className="text-xs text-gray-600 uppercase">Pass Marks</p>
              <p className="font-semibold text-gray-900">{test.pass_marks || 'N/A'}</p>
            </div>
            <div className="bg-orange-50 p-3 rounded">
              <p className="text-xs text-gray-600 uppercase">Duration</p>
              <p className="font-semibold text-gray-900">{test.duration_minutes} min</p>
            </div>
          </div>
        </div>

        {test.description && (
          <div className="mb-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Instructions</h3>
            <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 rounded">
              <p className="text-gray-700 whitespace-pre-wrap">{test.description}</p>
            </div>
          </div>
        )}

        {/* Test Form */}
        <form onSubmit={handleSubmitTest} className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Your Marks Obtained <span className="text-red-500">*</span>
            </label>
            <div className="flex gap-3">
              <input
                type="number"
                value={marks}
                onChange={(e) => setMarks(e.target.value)}
                placeholder="Enter marks obtained"
                min="0"
                max={test.total_marks}
                step="0.5"
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
              <div className="flex items-center gap-2 px-4 py-2 bg-gray-100 rounded-lg">
                <span className="text-sm text-gray-600">/ {test.total_marks}</span>
              </div>
            </div>
            {marks && (
              <div className="mt-2 text-sm">
                <p className="text-gray-600">
                  Percentage: <span className="font-semibold text-blue-600">
                    {((parseFloat(marks) / test.total_marks) * 100).toFixed(2)}%
                  </span>
                </p>
                {test.pass_marks && (
                  <p className={`mt-1 ${
                    parseFloat(marks) >= test.pass_marks ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {parseFloat(marks) >= test.pass_marks ? (
                      <CheckCircle className="inline mr-1" size={16} />
                    ) : (
                      <AlertCircle className="inline mr-1" size={16} />
                    )}
                    {parseFloat(marks) >= test.pass_marks ? 'Pass' : 'Fail'} (Pass marks: {test.pass_marks})
                  </p>
                )}
              </div>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Additional Notes (Optional)
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Add any comments or notes about the test..."
              rows="4"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Warning */}
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex gap-3">
              <AlertCircle className="text-red-600 flex-shrink-0" size={20} />
              <div className="text-sm text-red-800">
                <p className="font-semibold mb-1">Important</p>
                <p>Once you submit the test, you cannot make changes. Make sure all information is correct before submitting.</p>
              </div>
            </div>
          </div>

          {/* Submit Button */}
          <div className="flex gap-4">
            <button
              type="submit"
              disabled={submitting || !marks}
              className="flex-1 px-6 py-3 bg-green-600 text-white font-semibold rounded-lg hover:bg-green-700 disabled:bg-gray-400 transition-colors flex items-center justify-center gap-2"
            >
              <Send size={20} />
              {submitting ? 'Submitting...' : 'Submit Test'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function TestInstructions({ test, onStart }) {
  const [showDetails, setShowDetails] = useState(true)

  const isUpcoming = new Date(test.scheduled_date) > new Date()
  const hasEnded = new Date(test.scheduled_end_time) <= new Date()

  return (
    <div className="max-w-2xl mx-auto">
      <div className="bg-white rounded-lg shadow-lg p-8">
        {/* Title */}
        <h1 className="text-3xl font-bold text-gray-900 mb-4">{test.title}</h1>

        {/* Status Alert */}
        {isUpcoming && (
          <div className="mb-6 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <p className="text-yellow-800">
              ⏰ This test will start on {new Date(test.scheduled_date).toLocaleString()}
            </p>
          </div>
        )}

        {hasEnded && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-800">
              ❌ This test has ended. {!test.allow_late_submission && 'Late submissions are not allowed.'}
            </p>
          </div>
        )}

        {/* Description */}
        {test.description && (
          <div className="mb-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-3">Test Instructions</h2>
            <div className="bg-blue-50 border-l-4 border-blue-400 p-4 rounded">
              <p className="text-gray-700 whitespace-pre-wrap">{test.description}</p>
            </div>
          </div>
        )}

        {/* Quick Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-gradient-to-br from-blue-50 to-blue-100 p-4 rounded-lg">
            <p className="text-xs text-gray-600 uppercase font-semibold">Total Marks</p>
            <p className="text-3xl font-bold text-blue-600 mt-1">{test.total_marks}</p>
          </div>
          <div className="bg-gradient-to-br from-green-50 to-green-100 p-4 rounded-lg">
            <p className="text-xs text-gray-600 uppercase font-semibold">Duration</p>
            <p className="text-3xl font-bold text-green-600 mt-1">{test.duration_minutes}min</p>
          </div>
          <div className="bg-gradient-to-br from-purple-50 to-purple-100 p-4 rounded-lg">
            <p className="text-xs text-gray-600 uppercase font-semibold">Pass Marks</p>
            <p className="text-3xl font-bold text-purple-600 mt-1">{test.pass_marks || 'N/A'}</p>
          </div>
          <div className="bg-gradient-to-br from-orange-50 to-orange-100 p-4 rounded-lg">
            <p className="text-xs text-gray-600 uppercase font-semibold">Level</p>
            <p className="text-lg font-bold text-orange-600 mt-1 capitalize">{test.difficulty_level}</p>
          </div>
        </div>

        {/* Detailed Instructions */}
        <div className="bg-gray-50 rounded-lg p-6 mb-6">
          <h3 className="font-semibold text-gray-900 mb-4">Test Details</h3>
          <div className="space-y-3 text-sm text-gray-700">
            <div className="flex gap-3">
              <span className="text-blue-600 font-bold">📅</span>
              <div>
                <p className="font-medium">Start Date & Time</p>
                <p>{new Date(test.scheduled_date).toLocaleString()}</p>
              </div>
            </div>
            <div className="flex gap-3">
              <span className="text-red-600 font-bold">⏰</span>
              <div>
                <p className="font-medium">End Date & Time</p>
                <p>{new Date(test.scheduled_end_time).toLocaleString()}</p>
              </div>
            </div>
            <div className="flex gap-3">
              <span className="text-green-600 font-bold">⚡</span>
              <div>
                <p className="font-medium">Time Limit</p>
                <p>{test.duration_minutes} minutes from start</p>
              </div>
            </div>
            <div className="flex gap-3">
              <span className="text-purple-600 font-bold">✅</span>
              <div>
                <p className="font-medium">Late Submission</p>
                <p>{test.allow_late_submission ? 'Allowed' : 'Not allowed'}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Important Notes */}
        <div className="bg-red-50 border-l-4 border-red-400 p-4 rounded mb-6">
          <h4 className="font-semibold text-red-900 mb-2">⚠️ Important Guidelines</h4>
          <ul className="text-sm text-red-800 space-y-1">
            <li>• Once you start the test, a timer will begin</li>
            <li>• You must complete the test within the given time limit</li>
            <li>• Ensure you have a stable internet connection</li>
            <li>• Your answers will be automatically submitted when time runs out</li>
            <li>• Refresh or close the page may result in loss of progress</li>
          </ul>
        </div>

        {/* Start Button */}
        <button
          onClick={onStart}
          disabled={isUpcoming || hasEnded}
          className={`w-full py-3 px-6 font-bold text-lg rounded-lg transition-colors flex items-center justify-center gap-2 ${
            isUpcoming || hasEnded
              ? 'bg-gray-400 text-gray-600 cursor-not-allowed'
              : 'bg-green-600 text-white hover:bg-green-700'
          }`}
        >
          <CheckCircle size={24} />
          {isUpcoming ? 'Test not started yet' : hasEnded ? 'Test has ended' : 'Start Test'}
        </button>
      </div>
    </div>
  )
}
