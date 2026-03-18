import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Form, Input, Button, MessagePlugin } from 'tdesign-react'
import { LockOnIcon, MailIcon } from 'tdesign-icons-react'
import { adminLogin } from '../api/adminApi'

const { FormItem } = Form

export default function LoginPage() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)

  const handleLogin = async () => {
    if (!email || !password) {
      MessagePlugin.warning('请输入邮箱和密码')
      return
    }

    setLoading(true)
    try {
      const res = await adminLogin(email, password)
      localStorage.setItem('admin_token', res.access_token)
      if (res.refresh_token) {
        localStorage.setItem('admin_refresh_token', res.refresh_token)
      }
      MessagePlugin.success('登录成功')
      navigate('/', { replace: true })
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : '登录失败'
      MessagePlugin.error(message)
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleLogin()
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-white to-purple-50">
      <div className="w-full max-w-md px-4">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500 to-purple-600 shadow-lg mb-4">
            <span className="text-white font-bold text-2xl">AI</span>
          </div>
          <h1 className="text-2xl font-bold text-gray-800">AI Parenting 管理后台</h1>
          <p className="text-gray-500 mt-2">请使用管理员账号登录</p>
        </div>

        <Card className="shadow-xl border-0" style={{ borderRadius: 16 }}>
          <Form layout="vertical" onKeyDown={handleKeyDown}>
            <FormItem label="邮箱">
              <Input
                prefixIcon={<MailIcon />}
                value={email}
                onChange={(val) => setEmail(val as string)}
                placeholder="admin@example.com"
                size="large"
              />
            </FormItem>

            <FormItem label="密码">
              <Input
                prefixIcon={<LockOnIcon />}
                type="password"
                value={password}
                onChange={(val) => setPassword(val as string)}
                placeholder="请输入密码"
                size="large"
              />
            </FormItem>

            <Button
              theme="primary"
              block
              size="large"
              loading={loading}
              onClick={handleLogin}
              style={{ marginTop: 8, borderRadius: 8 }}
            >
              登录
            </Button>
          </Form>
        </Card>

        <p className="text-center text-gray-400 text-xs mt-6">
          仅限管理员使用 · AI Parenting v0.3.0
        </p>
      </div>
    </div>
  )
}
