<template>
  <header class="page-header" :class="[`page-header--${variant}`, { 'is-emphasis': emphasis }]">
    <div v-if="$slots.leading" class="page-header__leading">
      <slot name="leading" />
    </div>
    <div class="page-header__content">
      <p v-if="eyebrow" class="page-header__eyebrow">{{ eyebrow }}</p>
      <h1 class="page-header__title"><slot>{{ title }}</slot></h1>
      <p v-if="description" class="page-header__desc">{{ description }}</p>
    </div>
    <div v-if="$slots.actions" class="page-header__actions">
      <slot name="actions" />
    </div>
  </header>
</template>

<script setup lang="ts">
defineProps<{
  title?: string
  eyebrow?: string
  description?: string
  /** card | toolbar | plain */
  variant?: 'card' | 'toolbar' | 'plain'
  emphasis?: boolean
}>()
</script>
