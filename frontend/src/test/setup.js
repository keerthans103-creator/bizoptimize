import "@testing-library/jest-dom";

// jsdom doesn't implement the Pointer Events capture API at all -- real
// browsers do, so this is a test-environment gap, not app behavior to fix.
if (!Element.prototype.setPointerCapture) {
  Element.prototype.setPointerCapture = () => {};
}
if (!Element.prototype.releasePointerCapture) {
  Element.prototype.releasePointerCapture = () => {};
}
if (!Element.prototype.hasPointerCapture) {
  Element.prototype.hasPointerCapture = () => false;
}
