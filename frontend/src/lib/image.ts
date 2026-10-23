/** Shrinks a camera photo in the browser before upload: phone photos are 3-8 MB, which is slow on rural networks. */

const MAX_SIDE = 1600;
const KEEP_AS_IS_BYTES = 1.5 * 1024 * 1024;

export async function prepareForUpload(file: Blob): Promise<Blob> {
  try {
    // "from-image" applies the phone's rotation, so the upload is upright
    const bitmap = await createImageBitmap(file, { imageOrientation: "from-image" });
    const longest = Math.max(bitmap.width, bitmap.height);
    if (longest <= MAX_SIDE && file.size <= KEEP_AS_IS_BYTES) {
      bitmap.close();
      return file;
    }
    const scale = Math.min(1, MAX_SIDE / longest);
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(bitmap.width * scale);
    canvas.height = Math.round(bitmap.height * scale);
    canvas.getContext("2d")!.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    bitmap.close();
    const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.88));
    return blob ?? file;
  } catch {
    return file; // old browser or unreadable file: let the server decide
  }
}
