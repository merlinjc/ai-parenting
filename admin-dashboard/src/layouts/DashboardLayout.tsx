import { useState } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Menu, Layout, Avatar, Dropdown, Button } from 'tdesign-react'
import {
  DashboardIcon,
  ChartAnalyticsIcon,
  Setting1Icon,
  UserCircleIcon,
  LogoutIcon,
  NotificationIcon,
} from 'tdesign-icons-react'

const { MenuItem } = Menu
const { Header, Aside, Content } = Layout

export default function DashboardLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const [collapsed, setCollapsed] = useState(false)

  const menuItems = [
    { value: '/push-rules', label: '推送规则', icon: <DashboardIcon /> },
    { value: '/channel-monitor', label: '渠道监控', icon: <ChartAnalyticsIcon /> },
  ]

  const currentPath = location.pathname

  return (
    <Layout className="min-h-screen">
      {/* 顶部导航栏 */}
      <Header className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-6 h-16 bg-white border-b border-gray-100 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-primary-light flex items-center justify-center">
              <span className="text-white font-bold text-sm">AI</span>
            </div>
            <span className="text-lg font-semibold text-gray-800">AI Parenting 管理后台</span>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <Button variant="text" shape="square" icon={<NotificationIcon />} />
          <Dropdown
            options={[
              { content: '个人设置', value: 'settings', prefixIcon: <Setting1Icon /> },
              { content: '退出登录', value: 'logout', prefixIcon: <LogoutIcon /> },
            ]}
            onClick={(data) => {
              if (data.value === 'logout') {
                console.log('logout')
              }
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
        <Aside className="fixed left-0 top-16 bottom-0 z-40 bg-white border-r border-gray-100 shadow-sm overflow-y-auto"
          style={{ width: collapsed ? 64 : 220 }}
        >
          <Menu
            value={currentPath}
            collapsed={collapsed}
            expandMutex={false}
            style={{ marginTop: 8 }}
            onChange={(val) => navigate(val as string)}
          >
            <div className="px-4 py-3">
              <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">
                {!collapsed && '推送管理'}
              </span>
            </div>
            {menuItems.map((item) => (
              <MenuItem key={item.value} value={item.value} icon={item.icon}>
                {item.label}
              </MenuItem>
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
          className="transition-all duration-300 p-6 min-h-[calc(100vh-64px)]"
          style={{ marginLeft: collapsed ? 64 : 220 }}
        >
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
