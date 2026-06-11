import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDropzone } from 'react-dropzone'
import toast from 'react-hot-toast'
import { FileText, Presentation, Code2, Upload, CheckCircle2, X, Sparkles, ArrowRight } from 'lucide-react'
import { submissionsApi } from '../services/api'
import Spinner from '../components/ui/Spinner'

type FileKey = 'report' | 'ppt' | 'code_zip'

interface FileZoneProps {
  fileKey: FileKey
  label: string
  accept: Record<string, string[]>
  icon: React.ReactNode
  file: File | null
  onDrop: (f: File) => void
  onRemove: () => void
}

function FileDropZone({ fileKey, label, accept, icon, file, onDrop, onRemove }: FileZoneProps) {
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: (accepted) => { if (accepted[0]) onDrop(accepted[0]) },
    accept,
    multiple: false,
  })
  return (
    <div>
      <div className="flex items-center gap-2 mb-2">{icon}<span className="text-sm font-medium text-slate-300">{label}</span></div>
      {file ? (
        <div className="flex items-center justify-between bg-green-500/10 border border-green-500/20 rounded-xl px-4 py-3">
          <div className="flex items-center gap-2">
            <CheckCircle2 size={16} className="text-green-400" />
            <span className="text-sm text-green-300 font-medium">{file.name}</span>
            <span className="text-xs text-slate-500">({(file.size / 1024).toFixed(0)} KB)</span>
          </div>
          <button type="button" onClick={onRemove} className="text-slate-500 hover:text-red-400 transition-colors">
            <X size={15} />
          </button>
        </div>
      ) : (
        <div {...getRootProps()} className={`border-2 border-dashed rounded-xl px-4 py-6 text-center cursor-pointer transition-all duration-200
          ${isDragActive ? 'border-brand-500/60 bg-brand-500/5' : 'border-white/10 hover:border-white/20 bg-transparent hover:bg-white/5'}`}>
          <input {...getInputProps()} />
          <p className="text-sm text-slate-500">{isDragActive ? 'Drop here...' : 'Drag & drop or click to browse'}</p>
          <p className="text-xs text-slate-600 mt-0.5">{Object.values(accept).flat().join(', ').toUpperCase()}</p>
        </div>
      )}
    </div>
  )
}

export default function UploadPage() {
  const navigate = useNavigate()
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [loading, setLoading] = useState(false)
  const [files, setFiles] = useState<Record<FileKey, File | null>>({ report: null, ppt: null, code_zip: null })

  const setFile = (key: FileKey, file: File | null) => setFiles(prev => ({ ...prev, [key]: file }))

  const fileConfigs: { key: FileKey; label: string; accept: Record<string, string[]>; icon: React.ReactNode }[] = [
    {
      key: 'report', label: 'Project Report (PDF)',
      accept: { 'application/pdf': ['.pdf'] },
      icon: <FileText size={18} className="text-red-400" />
    },
    {
      key: 'ppt', label: 'Presentation (PPTX)',
      accept: { 'application/vnd.openxmlformats-officedocument.presentationml.presentation': ['.pptx'], 'application/vnd.ms-powerpoint': ['.ppt'] },
      icon: <Presentation size={18} className="text-orange-400" />
    },
    {
      key: 'code_zip', label: 'Source Code (ZIP)',
      accept: { 'application/zip': ['.zip'], 'application/x-zip-compressed': ['.zip'] },
      icon: <Code2 size={18} className="text-green-400" />
    },
  ]

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim()) { toast.error('Please enter a project title.'); return }
    if (!files.report && !files.ppt && !files.code_zip) { toast.error('Upload at least one file.'); return }

    const formData = new FormData()
    formData.append('title', title)
    if (description) formData.append('description', description)
    if (files.report) formData.append('report', files.report)
    if (files.ppt) formData.append('ppt', files.ppt)
    if (files.code_zip) formData.append('code_zip', files.code_zip)

    setLoading(true)
    try {
      await submissionsApi.upload(formData)
      toast.success('Project uploaded! AI is analyzing your content...')
      navigate('/dashboard')
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Upload failed. Please try again.')
    } finally { setLoading(false) }
  }

  return (
    <div className="max-w-2xl space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white mb-1">Upload Project</h1>
        <p className="text-slate-400 text-sm">The AI will analyze your files and generate personalized viva questions.</p>
      </div>

      {/* AI info banner */}
      <div className="flex items-start gap-3 px-4 py-3 rounded-xl bg-brand-500/10 border border-brand-500/20">
        <Sparkles size={16} className="text-brand-400 mt-0.5 shrink-0" />
        <p className="text-sm text-brand-200">
          After upload, AI reads your entire project and builds a knowledge map. Questions will reference your actual code, decisions, and technologies.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Project info */}
        <div className="glass-card space-y-4">
          <h2 className="font-semibold text-slate-200">Project Details</h2>
          <div>
            <label className="label">Project Title *</label>
            <input className="input" value={title} onChange={e => setTitle(e.target.value)}
              placeholder="e.g. E-Commerce Platform using FastAPI" required />
          </div>
          <div>
            <label className="label">Description <span className="text-slate-600">(optional)</span></label>
            <textarea className="input resize-none" rows={3} value={description}
              onChange={e => setDescription(e.target.value)}
              placeholder="Brief description of your project goals and approach..." />
          </div>
        </div>

        {/* File uploads */}
        <div className="glass-card space-y-4">
          <h2 className="font-semibold text-slate-200">Upload Files</h2>
          <p className="text-xs text-slate-500">Upload at least one file. More files = more specific questions.</p>
          {fileConfigs.map(({ key, label, accept, icon }) => (
            <FileDropZone key={key} fileKey={key} label={label} accept={accept} icon={icon}
              file={files[key]} onDrop={f => setFile(key, f)} onRemove={() => setFile(key, null)} />
          ))}
        </div>

        <button type="submit" className="btn-primary w-full justify-center py-3.5 text-sm" disabled={loading}>
          {loading
            ? <><Spinner size="sm" /> Uploading & Analyzing...</>
            : <><Upload size={16} /> Upload & Analyze Project <ArrowRight size={15} /></>}
        </button>
      </form>
    </div>
  )
}
