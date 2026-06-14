/**
 * 弹簧物理动画工具。
 *
 * 用法：
 * ```ts
 * const pos = useSpring(0, { stiffness: 180, damping: 24 })
 * pos.value = 3  // 弹簧驱动到 3
 * ```
 *
 * 原理：每一帧根据胡克定律 + 阻尼计算加速度，
 * 驱动 value 向目标值逼近，静止后自动停止 rAF 循环。
 */
import { type Ref, readonly, ref, watchEffect, onUnmounted } from 'vue'

export interface SpringConfig {
  /** 弹簧刚度，越大越快（默认 180） */
  stiffness?: number
  /** 阻尼系数，越大越不弹（默认 24） */
  damping?: number
  /** 质量（默认 1） */
  mass?: number
  /** 精度阈值，达到此误差内停止动画（默认 0.5） */
  precision?: number
}

const DEFAULTS = {
  stiffness: 180,
  damping: 24,
  mass: 1,
  precision: 0.5
} satisfies Required<SpringConfig>

interface SpringHandle {
  /** 当前弹簧位置（只读） */
  value: Readonly<Ref<number>>
  /** 为 current 和 target 同时增加一个偏移量（无动画），用于无限循环无缝边界复位 */
  // eslint-disable-next-line no-unused-vars
  jump: (_offset: number) => void
}

/**
 * 创建一个弹簧驱动的响应式数值。
 * 修改 targetRef.value 会自动触发弹簧动画。
 */
export function useSpring(targetRef: Ref<number>, config: SpringConfig = {}): SpringHandle {
  const { stiffness, damping, mass, precision } = { ...DEFAULTS, ...config }
  const current = ref(targetRef.value)
  let velocity = 0
  let frameId: number | null = null
  let running = true
  let lastTime = performance.now()

  function tick(now: number) {
    if (!running) return
    const dt = Math.min((now - lastTime) / 1000, 0.032)
    lastTime = now

    const displacement = current.value - targetRef.value
    const springForce = -stiffness * displacement
    const dampingForce = -damping * velocity
    const acceleration = (springForce + dampingForce) / mass
    velocity += acceleration * dt
    current.value += velocity * dt

    if (Math.abs(velocity) < 0.01 && Math.abs(displacement) < precision) {
      current.value = targetRef.value
      velocity = 0
      frameId = null
      return
    }

    frameId = requestAnimationFrame(tick)
  }

  function start() {
    lastTime = performance.now()
    if (frameId === null) {
      frameId = requestAnimationFrame(tick)
    }
  }

  /** 为 current 和 target 同时增加一个偏移量（无动画），用于无限循环无缝边界复位。
   *  offset 为整数时不会引入小数漂移，弹簧动量得以保留。 */
  function jump(offset: number) {
    current.value += offset
    targetRef.value += offset
    // 不重置 velocity——保留动量防止视觉卡顿
  }

  const stopWatch = watchEffect(() => {
    void targetRef.value
    start()
  })

  onUnmounted(() => {
    running = false
    if (frameId !== null) {
      cancelAnimationFrame(frameId)
      frameId = null
    }
    stopWatch()
  })

  return { value: readonly(current), jump }
}

// eslint-disable-next-line no-unused-vars
type SpringCallback = (_x: number) => void

/**
 * 单次弹簧动画（非响应式）。
 * 返回 cancel 函数。
 */
export function animateSpring(
  from: number,
  to: number,
  onUpdate: SpringCallback,
  config: SpringConfig = {}
): () => void {
  const { stiffness, damping, mass, precision } = { ...DEFAULTS, ...config }
  let position = from
  let velocity = 0
  let frameId: number | null = null
  let running = true
  let lastTime = performance.now()

  function tick(now: number) {
    if (!running) return
    const dt = Math.min((now - lastTime) / 1000, 0.032)
    lastTime = now

    const displacement = position - to
    const springForce = -stiffness * displacement
    const dampingForce = -damping * velocity
    const acceleration = (springForce + dampingForce) / mass
    velocity += acceleration * dt
    position += velocity * dt

    onUpdate(position)

    if (Math.abs(velocity) < 0.01 && Math.abs(displacement) < precision) {
      onUpdate(to)
      return
    }

    frameId = requestAnimationFrame(tick)
  }

  frameId = requestAnimationFrame(tick)

  return () => {
    running = false
    if (frameId !== null) {
      cancelAnimationFrame(frameId)
      frameId = null
    }
  }
}
