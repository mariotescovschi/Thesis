import { api } from '@/shared/api/client';
import type { Project } from '@/features/projects';

export interface FloorUploadItem {
  file: File;
  name: string;
  description?: string;
}

export const floorplansApi = {
  upload: (projectId: string, items: FloorUploadItem[]) => {
    const form = new FormData();
    items.forEach((it) => form.append('files', it.file));
    form.append(
      'meta',
      JSON.stringify(items.map((i) => ({ name: i.name, description: i.description ?? '' }))),
    );
    return api.postForm<Project>(`/projects/${projectId}/floors`, form);
  },
};
