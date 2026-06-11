import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { Copy, Trash2, Users, Plus, Edit2 } from 'lucide-react'
import api from '../../services/api'

export default function ClassroomManagement() {
  const { classroomId } = useParams()
  const navigate = useNavigate()
  const [classroom, setClassroom] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('overview')
  const [showEditModal, setShowEditModal] = useState(false)
  const [editData, setEditData] = useState({ name: '', description: '' })

  useEffect(() => {
    fetchClassroom()
  }, [classroomId])

  const fetchClassroom = async () => {
    try {
      setLoading(true)
      const response = await api.get(`/api/classrooms/${classroomId}`)
      setClassroom(response.data)
      setEditData({
        name: response.data.name,
        description: response.data.description || ''
      })
      setError(null)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load classroom')
      toast.error('Failed to load classroom')
    } finally {
      setLoading(false)
    }
  }

  const copyClassroomCode = async () => {
    try {
      await navigator.clipboard.writeText(classroom.classroom_code)
      toast.success('Classroom code copied!')
    } catch {
      toast.error('Failed to copy code')
    }
  }

  const handleUpdateClassroom = async (e) => {
    e.preventDefault()
    try {
      const response = await api.put(`/api/classrooms/${classroomId}`, editData)
      setClassroom(response.data)
      setShowEditModal(false)
      toast.success('Classroom updated successfully!')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to update classroom')
    }
  }

  const handleDeleteClassroom = async () => {
    if (!window.confirm('Are you sure? This will delete the classroom and all associated data.')) {
      return
    }
    try {
      await api.delete(`/api/classrooms/${classroomId}`)
      toast.success('Classroom deleted successfully!')
      navigate('/dashboard')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to delete classroom')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    )
  }

  if (!classroom) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
        <p>{error || 'Classroom not found'}</p>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      {/* Header */}
      <div className="flex justify-between items-start mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">{classroom.name}</h1>
          <p className="text-gray-600 mt-2">{classroom.description}</p>
        </div>
        <button
          onClick={() => setShowEditModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          <Edit2 size={18} />
          Edit
        </button>
      </div>

      {/* Classroom Code Card */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-6 mb-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-3">Classroom Code</h3>
        <div className="flex items-center gap-3">
          <code className="text-2xl font-mono font-bold text-blue-600 tracking-widest">
            {classroom.classroom_code}
          </code>
          <button
            onClick={copyClassroomCode}
            className="p-2 bg-white hover:bg-gray-100 rounded-lg border border-gray-300"
            title="Copy code"
          >
            <Copy size={20} className="text-gray-600" />
          </button>
        </div>
        <p className="text-sm text-gray-600 mt-3">
          Share this code with students. They can use it to join your classroom.
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h4 className="text-sm font-medium text-gray-600">Total Students</h4>
          <p className="text-3xl font-bold text-blue-600 mt-2">{classroom.total_students}</p>
        </div>
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <h4 className="text-sm font-medium text-gray-600">Total Tests</h4>
          <p className="text-3xl font-bold text-green-600 mt-2">{classroom.total_tests}</p>
        </div>
        <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
          <h4 className="text-sm font-medium text-gray-600">Created</h4>
          <p className="text-sm font-medium text-gray-900 mt-2">
            {new Date(classroom.created_at).toLocaleDateString()}
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <div className="flex gap-8">
          <button
            onClick={() => setActiveTab('overview')}
            className={`py-3 px-1 border-b-2 font-medium transition-colors ${
              activeTab === 'overview'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-600 hover:text-gray-900'
            }`}
          >
            Overview
          </button>
          <button
            onClick={() => setActiveTab('students')}
            className={`py-3 px-1 border-b-2 font-medium transition-colors flex items-center gap-2 ${
              activeTab === 'students'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-600 hover:text-gray-900'
            }`}
          >
            <Users size={18} />
            Students
          </button>
          <button
            onClick={() => setActiveTab('tests')}
            className={`py-3 px-1 border-b-2 font-medium transition-colors ${
              activeTab === 'tests'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-600 hover:text-gray-900'
            }`}
          >
            Tests
          </button>
        </div>
      </div>

      {/* Tab Content */}
      <div>
        {activeTab === 'overview' && (
          <div className="space-y-4">
            <div>
              <h3 className="font-semibold text-gray-900">Quick Actions</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-3">
                <button
                  onClick={() => navigate(`/classroom/${classroomId}/tests/create`)}
                  className="flex items-center justify-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                >
                  <Plus size={18} />
                  Create Test
                </button>
                <button
                  onClick={() => setActiveTab('students')}
                  className="flex items-center justify-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
                >
                  <Users size={18} />
                  View Students
                </button>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'students' && (
          <ClassroomStudents classroomId={classroomId} />
        )}

        {activeTab === 'tests' && (
          <ClassroomTests classroomId={classroomId} />
        )}
      </div>

      {/* Danger Zone */}
      <div className="mt-8 pt-6 border-t border-gray-200">
        <h3 className="text-lg font-semibold text-red-600 mb-3">Danger Zone</h3>
        <button
          onClick={handleDeleteClassroom}
          className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
        >
          <Trash2 size={18} className="inline mr-2" />
          Delete Classroom
        </button>
      </div>

      {/* Edit Modal */}
      {showEditModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg p-6 max-w-md w-full">
            <h2 className="text-2xl font-bold text-gray-900 mb-4">Edit Classroom</h2>
            <form onSubmit={handleUpdateClassroom} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Classroom Name
                </label>
                <input
                  type="text"
                  value={editData.name}
                  onChange={(e) => setEditData({ ...editData, name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Description
                </label>
                <textarea
                  value={editData.description}
                  onChange={(e) => setEditData({ ...editData, description: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 min-h-[100px]"
                />
              </div>
              <div className="flex gap-3">
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  Save
                </button>
                <button
                  type="button"
                  onClick={() => setShowEditModal(false)}
                  className="flex-1 px-4 py-2 bg-gray-300 text-gray-900 rounded-lg hover:bg-gray-400"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

function ClassroomStudents({ classroomId }) {
  const [students, setStudents] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchStudents()
  }, [classroomId])

  const fetchStudents = async () => {
    try {
      const response = await api.get(`/api/classrooms/${classroomId}/students`)
      setStudents(response.data)
    } catch (err) {
      toast.error('Failed to load students')
    } finally {
      setLoading(false)
    }
  }

  const handleRemoveStudent = async (studentId) => {
    if (!window.confirm('Remove this student from classroom?')) return
    try {
      await api.delete(`/api/classrooms/${classroomId}/students/${studentId}`)
      setStudents(students.filter(s => s.student_id !== studentId))
      toast.success('Student removed')
    } catch (err) {
      toast.error('Failed to remove student')
    }
  }

  if (loading) {
    return <div className="text-center py-4">Loading...</div>
  }

  if (students.length === 0) {
    return (
      <div className="text-center py-8 text-gray-600">
        <p>No students enrolled yet. Share the classroom code to invite students!</p>
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b border-gray-200 bg-gray-50">
            <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Student ID</th>
            <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Enrolled</th>
            <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Status</th>
            <th className="px-4 py-3 text-right text-sm font-semibold text-gray-900">Actions</th>
          </tr>
        </thead>
        <tbody>
          {students.map(student => (
            <tr key={student.id} className="border-b border-gray-200 hover:bg-gray-50">
              <td className="px-4 py-3 text-sm text-gray-900">{student.student_id}</td>
              <td className="px-4 py-3 text-sm text-gray-600">
                {new Date(student.enrolled_at).toLocaleDateString()}
              </td>
              <td className="px-4 py-3 text-sm">
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                  student.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                }`}>
                  {student.is_active ? 'Active' : 'Inactive'}
                </span>
              </td>
              <td className="px-4 py-3 text-right">
                <button
                  onClick={() => handleRemoveStudent(student.student_id)}
                  className="text-red-600 hover:text-red-800 text-sm font-medium"
                >
                  Remove
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function ClassroomTests({ classroomId }) {
  const navigate = useNavigate()
  const [tests, setTests] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchTests()
  }, [classroomId])

  const fetchTests = async () => {
    try {
      const response = await api.get(`/api/classrooms/${classroomId}/tests`)
      setTests(response.data)
    } catch (err) {
      toast.error('Failed to load tests')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <div className="text-center py-4">Loading...</div>
  }

  if (tests.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-gray-600 mb-4">No tests created yet</p>
        <button
          onClick={() => navigate(`/classroom/${classroomId}/tests/create`)}
          className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          <Plus size={18} />
          Create First Test
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {tests.map(test => (
        <div
          key={test.id}
          onClick={() => navigate(`/classroom/${classroomId}/tests/${test.id}`)}
          className="border border-gray-200 rounded-lg p-4 hover:border-blue-400 hover:bg-blue-50 cursor-pointer transition-all"
        >
          <div className="flex justify-between items-start">
            <div>
              <h3 className="font-semibold text-gray-900">{test.title}</h3>
              <p className="text-sm text-gray-600 mt-1">{test.description}</p>
              <div className="flex gap-4 mt-2 text-sm text-gray-600">
                <span>📅 {new Date(test.scheduled_date).toLocaleDateString()}</span>
                <span>⏱️ {test.duration_minutes} mins</span>
                <span>📊 {test.total_marks} marks</span>
                <span className={`px-2 py-1 rounded text-xs font-medium ${
                  test.is_published ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                }`}>
                  {test.is_published ? 'Published' : 'Draft'}
                </span>
              </div>
            </div>
            <div className="text-right">
              <p className="text-lg font-semibold text-blue-600">{test.average_score.toFixed(1)}</p>
              <p className="text-xs text-gray-500">avg score</p>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
