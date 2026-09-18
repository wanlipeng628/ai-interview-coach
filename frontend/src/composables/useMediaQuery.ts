import { onBeforeUnmount, ref } from 'vue'

export const useMediaQuery = (query: string) => {
  const matches = ref(false)
  const mediaQuery = window.matchMedia(query)

  const sync = () => {
    matches.value = mediaQuery.matches
  }

  sync()
  mediaQuery.addEventListener('change', sync)
  onBeforeUnmount(() => mediaQuery.removeEventListener('change', sync))

  return matches
}
