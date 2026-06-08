declare module '@exuanbo/file-icons-js/dist/js/file-icons.esm.js' {
  interface FileIcons {
    getClass(name: string, options?: { color?: boolean; array?: boolean }): Promise<string>;
  }
  const icons: FileIcons;
  export default icons;
}
