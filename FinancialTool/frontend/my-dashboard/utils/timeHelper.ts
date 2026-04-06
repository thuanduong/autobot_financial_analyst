
export const formatDateTime = (unixSeconds: number) => {
  const date = new Date(unixSeconds * 1000);
  return date.toLocaleString('vi-VN', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
    hour12: false 
  });
};