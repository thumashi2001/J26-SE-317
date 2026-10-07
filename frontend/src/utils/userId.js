// IDs are checked only on the server, so the page never shows or explains an ID format.
// This just removes spaces and capitalises what the person types.
export const cleanId = (value) => value.replace(/\s/g, '').toUpperCase();
