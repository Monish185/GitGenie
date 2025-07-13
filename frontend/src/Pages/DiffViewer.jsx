function DiffViewer({ before, after, fileName }) {
  if (!before || !after || !fileName) {
    return (
      <div className="bg-red-50 border border-red-200 rounded p-4">
        <p className="text-red-600">❌ Invalid diff data: Missing required parameters</p>
      </div>
    );
  }

  try {
    const beforeStr = typeof before === 'string' ? before : String(before);
    const afterStr = typeof after === 'string' ? after : String(after);

    const generateDiff = (oldText, newText) => {
      const oldLines = oldText.split('\n');
      const newLines = newText.split('\n');
      const diff = [];
      
      let oldIndex = 0;
      let newIndex = 0;
      
      while (oldIndex < oldLines.length || newIndex < newLines.length) {
        const oldLine = oldLines[oldIndex];
        const newLine = newLines[newIndex];
        
        if (oldIndex >= oldLines.length) {
          diff.push({
            type: 'addition',
            content: newLine,
            oldLineNumber: null,
            newLineNumber: newIndex + 1
          });
          newIndex++;
        } else if (newIndex >= newLines.length) {
          diff.push({
            type: 'deletion',
            content: oldLine,
            oldLineNumber: oldIndex + 1,
            newLineNumber: null
          });
          oldIndex++;
        } else if (oldLine === newLine) {
          diff.push({
            type: 'context',
            content: oldLine,
            oldLineNumber: oldIndex + 1,
            newLineNumber: newIndex + 1
          });
          oldIndex++;
          newIndex++;
        } else {
          
          const nextOldLine = oldLines[oldIndex + 1];
          const nextNewLine = newLines[newIndex + 1];
          
          if (nextOldLine === newLine) {
            diff.push({
              type: 'deletion',
              content: oldLine,
              oldLineNumber: oldIndex + 1,
              newLineNumber: null
            });
            oldIndex++;
          } else if (nextNewLine === oldLine) {
            diff.push({
              type: 'addition',
              content: newLine,
              oldLineNumber: null,
              newLineNumber: newIndex + 1
            });
            newIndex++;
          } else {
            diff.push({
              type: 'deletion',
              content: oldLine,
              oldLineNumber: oldIndex + 1,
              newLineNumber: null
            });
            diff.push({
              type: 'addition',
              content: newLine,
              oldLineNumber: null,
              newLineNumber: newIndex + 1
            });
            oldIndex++;
            newIndex++;
          }
        }
      }
      
      return diff;
    };

    const diffLines = generateDiff(beforeStr, afterStr);

    const hasChanges = diffLines.some(line => line.type !== 'context');
    
    if (!hasChanges) {
      return (
        <div className="bg-yellow-50 border border-yellow-200 rounded p-4">
          <p className="text-yellow-600">⚠️ No differences found between files</p>
        </div>
      );
    }

    const getLineStyle = (type) => {
      switch (type) {
        case 'addition':
          return 'bg-green-50 border-l-4 border-green-500';
        case 'deletion':
          return 'bg-red-50 border-l-4 border-red-500';
        case 'context':
          return 'bg-white border-l-4 border-gray-200';
        default:
          return 'bg-gray-50 border-l-4 border-gray-300';
      }
    };

    const getLinePrefix = (type) => {
      switch (type) {
        case 'addition':
          return '+';
        case 'deletion':
          return '-';
        default:
          return ' ';
      }
    };

    const getTextColor = (type) => {
      switch (type) {
        case 'addition':
          return 'text-green-800';
        case 'deletion':
          return 'text-red-800';
        default:
          return 'text-gray-800';
      }
    };

    return (
      <div className="diff-container border border-gray-200 rounded-lg overflow-hidden">
        
        <div className="bg-gray-800 text-white px-4 py-3 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <span className="font-mono font-medium">{fileName}</span>
          </div>
          <div className="text-sm text-gray-300">
            +{diffLines.filter(d => d.type === 'addition').length} -{diffLines.filter(d => d.type === 'deletion').length}
          </div>
        </div>

      
        <div className="bg-gray-50 overflow-x-auto">
          <div className="font-mono text-sm bg-white">
            {diffLines.map((line, index) => (
              <div key={index} className={`flex ${getLineStyle(line.type)} min-h-[1.5rem]`}>
                <div className="w-12 text-right text-gray-500 px-2 py-1 select-none border-r border-gray-300 flex-shrink-0">
                  {line.oldLineNumber || ''}
                </div>
                <div className="w-12 text-right text-gray-500 px-2 py-1 select-none border-r border-gray-300 flex-shrink-0">
                  {line.newLineNumber || ''}
                </div>
                <div className={`px-3 py-1 flex-1 ${getTextColor(line.type)}`}>
                  <span className="text-gray-400 mr-1">{getLinePrefix(line.type)}</span>
                  <span className="whitespace-pre-wrap">{line.content}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );

  } catch (error) {
    console.error('DiffViewer Error:', error);
    console.error('Before content:', before);
    console.error('After content:', after);
    console.error('File name:', fileName);
    
    return (
      <div className="bg-red-50 border border-red-200 rounded p-4">
        <p className="text-red-600 font-semibold">❌ Error generating diff view</p>
        <p className="text-red-500 text-sm mt-2">
          {error.message || 'Unknown error occurred'}
        </p>
        <details className="mt-2">
          <summary className="text-red-500 text-sm cursor-pointer">Show fallback comparison</summary>
          <div className="mt-2 grid grid-cols-2 gap-4">
            <div>
              <h4 className="font-medium text-gray-700">Before:</h4>
              <pre className="bg-gray-100 p-2 rounded text-xs overflow-auto max-h-40">
                {beforeStr}
              </pre>
            </div>
            <div>
              <h4 className="font-medium text-gray-700">After:</h4>
              <pre className="bg-gray-100 p-2 rounded text-xs overflow-auto max-h-40">
                {afterStr}
              </pre>
            </div>
          </div>
        </details>
      </div>
    );
  }
}

export default DiffViewer;