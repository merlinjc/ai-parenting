import { useState } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Menu, Layout, Avatar, Dropdown, Button } from 'tdesign-react'
import {
  DashboardIcon,
  ChartAnalyticsIcon,
  UserCircleIcon,
  LogoutIcon,
  NotificationIcon,
  ChatIcon,
  RootListIcon,
  ChartBubbleIcon,
  ServerIcon,
  MailIcon,
  TimeIcon,
  ControlPlatformIcon,
  LinkIcon,
} from 'tdesign-icons-react'

const { MenuItem, SubMenu } = Menu
const { Header, Aside, Content } = Layout

interface MenuGroup {
  label: string
  items: Array<{
    value: string
    label: string
    icon: React.ReactNode
  }>
}

const menuGroups: MenuGroup[] = [
  {
    label: '总览',
    items: [
      { value: '/dashboard', label: '仪表板', icon: <DashboardIcon /> },
    ],
  },
  {
    label: '用户与内容',
    items: [
      { value: '/users', label: '用户管理', icon: <UserCircleIcon /> },
      { value: '/children', label: '儿童管理', icon: <UserCircleIcon /> },
      { value: '/plans', label: '计划管理', icon: <ChartBubbleIcon /> },
      { value: '/records', label: '观察记录', icon: <RootListIcon /> },
    ],
  },
  {
    label: 'AI 与反馈',
    items: [
      { value: '/ai-sessions', label: 'AI 会话', icon: <ChatIcon /> },
      { value: '/weekly-feedbacks', label: '周反馈', icon: <TimeIcon /> },
    ],
  },
  {
    label: '推送与渠道',
    items: [
      { value: '/messages', label: '消息管理', icon: <MailIcon /> },
      { value: '/push-rules', label: '推送规则', icon: <ControlPlatformIcon /> },
      { value: '/push-logs', label: '推送日志', icon: <NotificationIcon /> },
      { value: '/channel-monitor', label: '渠道监控', icon: <ChartAnalyticsIcon /> },
    ],
  },
  {
    label: '系统',
    items: [
      { value: '/devices', label: '设备管理', icon: <ServerIcon /> },
    ],
  },
]

export default function DashboardLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const [collapsed, setCollapsed] = useState(false)

  const currentPath = location.pathname

  const handleLogout = () => {
    localStorage.removeItem('admin_token')
    localStorage.removeItem('admin_refresh_token')
    navigate('/login', { replace: true })
  }

  return (
    <Layout className="min-h-screen">
      {/* 顶部导航栏 */}
      <Header className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-6 h-16 bg-white border-b border-gray-100 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
              <span className="text-white font-bold text-sm">AI</span>
            </div>
            <span className="text-lg font-semibold text-gray-800">
              {collapsed ? '' : 'AI Parenting 管理后台'}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <Dropdown
            options={[
              { content: '退出登录', value: 'logout', prefixIcon: <LogoutIcon /> },
            ]}
            onClick={(data) => {
              if (data.value === 'logout') handleLogout()
            }}
          >
            <div className="flex items-center gap-2 cursor-pointer hover:opacity-80 transition-opacity">
              <Avatar size="small" icon={<UserCircleIcon />} />
              <span className="text-sm text-gray-600">管理员</span>
            </div>
          </Dropdown>
        </div>
      </Header>

      <Layout className="pt-16">
        {/* 侧边栏 */}
        <Aside
          className="fixed left-0 top-16 bottom-0 z-40 bg-white border-r border-gray-100 shadow-sm overflow-y-auto"
          style={{ width: collapsed ? 64 : 232 }}
        >
          <Menu
            value={currentPath}
            collapsed={collapsed}
            expandMutex={false}
            style={{ marginTop: 4 }}
            onChange={(val) => navigate(val as string)}
          >
            {menuGroups.map((group) => (
              <div key={group.label}>
                {!collapsed && (
                  <div className="px-4 pt-4 pb-1">
                    <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">
                      {group.label}
                    </span>
                  </div>
                )}
                {group.items.map((item) => (
                  <MenuItem key={item.value} value={item.value} icon={item.icon}>
                    {item.label}
                  </MenuItem>
                ))}
              </div>
            ))}
          </Menu>

          {/* 折叠按钮 */}
          <div className="absolute bottom-4 w-full flex justify-center">
            <Button
              variant="text"
              size="small"
              onClick={() => setCollapsed(!collapsed)}
              className="text-gray-400 hover:text-gray-600"
            >
              {collapsed ? '»' : '«'}
            </Button>
          </div>
        </Aside>

        {/* 主内容区 */}
        <Content
          className="transition-all duration-300 p-6 min-h-[calc(100vh-64px)] bg-gray-50"
          style={{ marginLeft: collapsed ? 64 : 232 }}
        >
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
