export const branchSelectStub = {
  name: 'BranchSelect',
  props: ['modelValue', 'options', 'placeholder'],
  emits: ['update:modelValue'],
  template: `<select class="form-select" :value="modelValue" @change="$emit('update:modelValue', $event.target.value)">
    <option value="">{{ placeholder || '请选择分公司' }}</option>
    <option v-for="option in options" :key="option.value" :value="option.value">{{ option.label }}</option>
  </select>`,
}
