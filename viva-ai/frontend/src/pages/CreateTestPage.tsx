import React, { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { ArrowLeft } from 'lucide-react'
import api from '../../services/api'

export default function CreateTestPage() {
  const { classroomId } = useParams()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    difficulty_level: 'medium',
    total_marks: 100,
    pass_marks: 40,
    duration_minutes: 60,
    scheduled_date: '',
    scheduled_end_time: '',
    allow_late_submission: false
  })

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()

    // Validation
    if (!formData.title.trim()) {
      toast.error('Test title is required')
      return
    }

    if (!formData.scheduled_date || !formData.scheduled_end_time) {
      toast.error('Please set start and end time')
      return
    }

    if (new Date(formData.scheduled_end_time) <= new Date(formData.scheduled_date)) {
      toast.error('End time must be after start time')
      return
    }

    if (formData.pass_marks > formData.total_marks) {
      toast.error('Pass marks cannot exceed total marks')
      return
    }

    try {
      setLoading(true)
      const response = await api.post(`/api/classrooms/${classroomId}/tests`, formData)
      toast.success('Test created successfully!')
      navigate(`/classroom/${classroomId}`)
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Failed to create test'
      toast.error(errorMsg)
      console.error('Error creating test:', err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 text-blue-600 hover:text-blue-800 mb-4"
        >
          <ArrowLeft size={20} />
          Back
        </button>
        <h1 className="text-3xl font-bold text-gray-900">Create New Test</h1>
        <p className="text-gray-600 mt-2">Set up a new test/exam for your classroom</p>
      </div>

      {/* Form */}
      <div className="bg-white rounded-lg shadow-lg p-8">
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Basic Info */}
          <div className="border-b border-gray-200 pb-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Test Information</h2>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Test Title <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                name="title"
                value={formData.title}
                onChange={handleInputChange}
                placeholder="e.g., Data Structures Quiz"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>

            <div className="mt-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Description
              </label>
              <textarea
                name="description"
                value={formData.description}
                onChange={handleInputChange}
                placeholder="Optional description of the test..."
                rows="3"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          {/* Test Configuration */}
          <div className="border-b border-gray-200 pb-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Test Configuration</h2>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Difficulty Level <span className="text-red-500">*</span>
                </label>
                <select
                  name="difficulty_level"
                  value={formData.difficulty_level}
                  onChange={handleInputChange}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="easy">Easy</option>
                  <option value="medium">Medium</option>
                  <option value="hard">Hard</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Total Marks <span className="text-red-500">*</span>
                </label>
                <input
                  type="number"
                  name="total_marks"
                  value={formData.total_marks}
                  onChange={handleInputChange}
                  min="1"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Pass Marks
                </label>
                <input
                  type="number"
                  name="pass_marks"
                  value={formData.pass_marks}
                  onChange={handleInputChange}
                  min="0"
                  max={formData.total_marks}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            <div className="mt-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Duration (Minutes) <span className="text-red-500">*</span>
              </label>
              <input
                type="number"
                name="duration_minutes"
                value={formData.duration_minutes}
                onChange={handleInputChange}
                min="1"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>
          </div>

          {/* Scheduling */}
          <div className="border-b border-gray-200 pb-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Scheduling</h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Start Date & Time <span className="text-red-500">*</span>
                </label>
                <input
                  type="datetime-local"
                  name="scheduled_date"
                  value={formData.scheduled_date}
                  onChange={handleInputChange}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  End Date & Time <span className="text-red-500">*</span>
                </label>
                <input
                  type="datetime-local"
                  name="scheduled_end_time"
                  value={formData.scheduled_end_time}
                  onChange={handleInputChange}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
            </div>

            <div className="mt-4">
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  name="allow_late_submission"
                  checked={formData.allow_late_submission}
                  onChange={handleInputChange}
                  className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                />
                <span className="text-sm font-medium text-gray-700">
                  Allow students to submit after deadline
                </span>
              </label>
              <p className="text-sm text-gray-500 mt-1 ml-7">
                If enabled, students can still submit their answers after the deadline
              </p>
            </div>
          </div>

          {/* Summary */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h3 className="font-semibold text-blue-900 mb-3">Test Summary</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
              <div>
                <p className="text-blue-700 font-medium">Total Marks</p>
                <p className="text-blue-900 text-lg font-bold">{formData.total_marks}</p>
              </div>
              <div>
                <p className="text-blue-700 font-medium">Pass Marks</p>
                <p className="text-blue-900 text-lg font-bold">{formData.pass_marks || 'N/A'}</p>
              </div>
              <div>
                <p className="text-blue-700 font-medium">Duration</p>
                <p className="text-blue-900 text-lg font-bold">{formData.duration_minutes} min</p>
              </div>
              <div>
                <p className="text-blue-700 font-medium">Difficulty</p>
                <p className="text-blue-900 text-lg font-bold capitalize">{formData.difficulty_level}</p>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-4 pt-6">
            <button
              type="submit"
              disabled={loading}
              className="flex-1 px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:bg-blue-400 transition-colors"
            >
              {loading ? 'Creating...' : 'Create Test'}
            </button>
            <button
              type="button"
              onClick={() => navigate(-1)}
              className="flex-1 px-6 py-3 bg-gray-300 text-gray-900 font-medium rounded-lg hover:bg-gray-400 transition-colors"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>

      {/* Info Box */}
      <div className="mt-6 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <h3 className="font-semibold text-yellow-900 mb-2">💡 Tips</h3>
        <ul className="text-sm text-yellow-800 space-y-1 ml-4">
          <li>• Set realistic deadlines to give students enough time to complete the test</li>
          <li>• You can edit the test details before publishing it to students</li>
          <li>• After publishing, students will see the test in their classroom</li>
          <li>• Set pass marks to automatically evaluate student performance</li>
        </ul>
      </div>
    </div>
  )
}
